#!/usr/bin/env python3
"""
XTTS Studio - Desktop Voice Synthesis & Cloning Studio
Lightweight Python server managing isolated Coqui XTTS v2 generation on CPU.
Includes auto-shutdown watchdog on window close.
"""

import http.server
import json
import mimetypes
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid
from email.parser import BytesParser
from email.policy import default

PORT = int(os.environ.get("XTTS_STUDIO_PORT", 5222))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
OUTPUT_DIR = os.path.expanduser("~/Music/AI_Voice")

DEFAULT_VENV = os.path.join(BASE_DIR, ".venv")
VENV_DIR = os.environ.get("XTTS_VENV", DEFAULT_VENV)

# Self-bootstrap into virtualenv if executed directly with system python
venv_python = os.path.join(VENV_DIR, "bin", "python")
if os.path.isfile(venv_python) and os.path.realpath(sys.executable) != os.path.realpath(venv_python):
    os.execv(venv_python, [venv_python] + sys.argv)

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

VOICE_FILE_EXTENSIONS = (".wav", ".mp3", ".flac")

# XTTS-v2's 58 built-in pretrained speakers (from speakers_xtts.pth, bundled
# with the model). Selectable via --speaker_idx instead of --speaker_wav,
# so no reference audio upload is needed for these.
BUILTIN_SPEAKERS = [
    "Aaron Dreschner", "Abrahan Mack", "Adde Michal", "Alexandra Hisakawa",
    "Alison Dietlinde", "Alma María", "Ana Florence", "Andrew Chipper",
    "Annmarie Nele", "Asya Anara", "Badr Odhiambo", "Baldur Sanjin",
    "Barbora MacLean", "Brenda Stern", "Camilla Holmström",
    "Chandra MacFarland", "Claribel Dervla", "Craig Gutsy", "Daisy Studious",
    "Damien Black", "Damjan Chapman", "Dionisio Schuyler",
    "Eugenio Mataracı", "Ferran Simen", "Filip Traverse",
    "Gilberto Mathias", "Gitta Nikolina", "Gracie Wise", "Henriette Usha",
    "Ige Behringer", "Ilkin Urbano", "Kazuhiko Atallah", "Kumar Dahl",
    "Lidiya Szekeres", "Lilya Stainthorpe", "Ludvig Milivoj", "Luis Moray",
    "Maja Ruoho", "Marcos Rudaski", "Narelle Moon", "Nova Hogarth",
    "Rosemary Okafor", "Royston Min", "Sofia Hellen", "Suad Qasim",
    "Szofi Granger", "Tammie Ema", "Tammy Grit", "Tanja Adelina",
    "Torcull Diarmuid", "Uta Obando", "Viktor Eka", "Viktor Menelaos",
    "Vjollca Johnnie", "Wulf Carlevaro", "Xavier Hayasaka",
    "Zacharie Aimilios", "Zofija Kendrick",
]

last_heartbeat = time.time()
has_received_heartbeat = False
server_instance = None

# In-Memory XTTS Engine & Concurrency Control
tts_engine = None
tts_lock = threading.Lock()
tts_loading = False
tts_load_error = None

def warm_tts_engine():
    """Asynchronously loads XTTS-v2 into RAM on CPU once at startup."""
    global tts_engine, tts_loading, tts_load_error
    if tts_engine is not None or tts_loading:
        return
    tts_loading = True
    try:
        print("⚡ Warming XTTS-v2 in-memory engine (CPU isolated)...")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        os.environ["ROCR_VISIBLE_DEVICES"] = ""
        os.environ["HIP_VISIBLE_DEVICES"] = ""
        os.environ["COQUI_TOS_AGREED"] = "1"
        from TTS.api import TTS
        engine = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cpu")
        with tts_lock:
            tts_engine = engine
            tts_loading = False
        print("🚀 XTTS-v2 engine is warm and resident in RAM!")
    except Exception as e:
        tts_loading = False
        tts_load_error = str(e)
        print(f"❌ Failed to warm XTTS engine: {e}")

def watchdog_loop():
    """Auto-shuts down if UI window is closed (no heartbeat for 10s)."""
    global last_heartbeat, has_received_heartbeat, server_instance
    while True:
        time.sleep(2)
        if has_received_heartbeat:
            elapsed = time.time() - last_heartbeat
            if elapsed > 10:
                print(f"⚠️ XTTS Studio closed (inactive for {elapsed:.1f}s). Shutting down...")
                if server_instance:
                    threading.Thread(target=server_instance.shutdown).start()
                os._exit(0)

class XTTSHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] {format % args}\n")
        sys.stdout.flush()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
        elif path.startswith("/static/"):
            rel = path[8:]
            self.serve_file(os.path.join(STATIC_DIR, rel))
        elif path == "/api/status":
            self.handle_api_status()
        elif path == "/api/voices":
            self.handle_api_voices()
        elif path.startswith("/api/voice_preview/"):
            fname = urllib.parse.unquote(path[19:])
            self.serve_file(os.path.join(VOICES_DIR, fname), "audio/wav")
        elif path.startswith("/api/audio/"):
            fname = urllib.parse.unquote(path[11:])
            self.serve_file(os.path.join(OUTPUT_DIR, fname), "audio/wav")
        elif path == "/api/history":
            self.handle_api_history()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/heartbeat":
            self.handle_heartbeat()
        elif path == "/api/synthesize":
            self.handle_api_synthesize()
        elif path == "/api/upload_voice":
            self.handle_upload_voice()
        elif path == "/api/open_folder":
            self.handle_open_folder()
        elif path == "/api/shutdown":
            self.handle_shutdown()
        else:
            self.send_error(404, "Not Found")

    def handle_heartbeat(self):
        global last_heartbeat, has_received_heartbeat
        last_heartbeat = time.time()
        has_received_heartbeat = True
        self.send_json({"ok": True})

    def handle_shutdown(self):
        self.send_json({"success": True, "message": "Exiting XTTS Studio..."})
        def perform_exit():
            time.sleep(0.5)
            os._exit(0)
        threading.Thread(target=perform_exit).start()

    def serve_file(self, filepath, content_type=None):
        if not os.path.isfile(filepath):
            self.send_error(404, f"File not found: {os.path.basename(filepath)}")
            return

        if not content_type:
            content_type, _ = mimetypes.guess_type(filepath)
            if not content_type:
                content_type = "application/octet-stream"

        file_size = os.path.getsize(filepath)
        range_header = self.headers.get("Range")

        try:
            if range_header and range_header.startswith("bytes="):
                ranges = range_header.replace("bytes=", "").split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                length = end - start + 1

                with open(filepath, "rb") as f:
                    f.seek(start)
                    chunk = f.read(length)

                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(chunk)
            else:
                with open(filepath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_error(500, f"Error streaming file: {e}")

    def send_json(self, data, status_code=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def handle_api_status(self):
        tts_bin = os.path.join(VENV_DIR, "bin", "python")
        is_ready = os.path.isfile(tts_bin) and os.access(tts_bin, os.X_OK)
        voices = [f for f in os.listdir(VOICES_DIR) if f.lower().endswith((".wav", ".mp3", ".flac"))]

        self.send_json({
            "ready": is_ready,
            "model_loaded": (tts_engine is not None),
            "model_loading": tts_loading,
            "model_error": tts_load_error,
            "engine": "Coqui XTTS v2 (Warm In-Memory CPU)",
            "venv_path": VENV_DIR,
            "voices_count": len(voices),
            "output_dir": OUTPUT_DIR
        })

    def handle_api_voices(self):
        voice_files = []
        for entry in os.scandir(VOICES_DIR):
            if entry.is_file() and entry.name.lower().endswith((".wav", ".mp3", ".flac")):
                stat = entry.stat()
                voice_files.append({
                    "name": entry.name,
                    "size": stat.st_size,
                    "url": f"/api/voice_preview/{urllib.parse.quote(entry.name)}"
                })
        voice_files.sort(key=lambda x: x["name"])
        self.send_json({"voices": voice_files, "builtin_speakers": BUILTIN_SPEAKERS})

    def handle_api_history(self):
        audios = []
        for entry in os.scandir(OUTPUT_DIR):
            if entry.is_file() and entry.name.lower().endswith((".wav", ".mp3")):
                stat = entry.stat()
                audios.append({
                    "name": entry.name,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "url": f"/api/audio/{urllib.parse.quote(entry.name)}"
                })
        audios.sort(key=lambda x: x["mtime"], reverse=True)
        self.send_json({"audios": audios, "count": len(audios)})

    def handle_open_folder(self):
        try:
            subprocess.Popen(["xdg-open", OUTPUT_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.send_json({"success": True, "path": OUTPUT_DIR})
        except Exception as e:
            self.send_json({"error": str(e)}, status_code=500)

    def handle_upload_voice(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json({"error": "Invalid Content-Type"}, status_code=400)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_data = self.rfile.read(length)
            msg = BytesParser(policy=default).parsebytes(
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8") + raw_data
            )
            for part in msg.iter_parts():
                filename = part.get_filename()
                if filename:
                    safe_name = os.path.basename(filename).replace(" ", "_")
                    if not safe_name.lower().endswith(".wav"):
                        safe_name += ".wav"
                    dest_path = os.path.join(VOICES_DIR, safe_name)
                    file_bytes = part.get_payload(decode=True)
                    with open(dest_path, "wb") as f:
                        f.write(file_bytes)
                    self.send_json({"success": True, "name": safe_name})
                    return

            self.send_json({"error": "No file content found in upload"}, status_code=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status_code=500)

    def handle_api_synthesize(self):
        global tts_engine, tts_loading, tts_load_error
        payload = self.read_json_body()
        text = payload.get("text", "").strip()
        voice_file = payload.get("voice", "narrator_default.wav")
        lang = payload.get("language", "en")

        if not text:
            self.send_json({"error": "Text is required"}, status_code=400)
            return

        # Engine readiness check (wait if background warm-up is in progress)
        if tts_engine is None:
            if tts_loading:
                for _ in range(60):
                    if tts_engine is not None:
                        break
                    time.sleep(0.5)
            if tts_engine is None:
                err = tts_load_error or "Engine is still warming up. Please try again in a few seconds."
                self.send_json({"error": err, "success": False}, status_code=503)
                return

        is_builtin = voice_file in BUILTIN_SPEAKERS or not voice_file.lower().endswith(VOICE_FILE_EXTENSIONS)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_filename = f"Voice_{timestamp}_{lang}.wav"
        out_path = os.path.join(OUTPUT_DIR, out_filename)

        t0 = time.time()
        try:
            with tts_lock:
                if is_builtin:
                    tts_engine.tts_to_file(
                        text=text,
                        speaker=voice_file,
                        language=lang,
                        file_path=out_path
                    )
                else:
                    speaker_path = os.path.join(VOICES_DIR, voice_file)
                    if not os.path.isfile(speaker_path):
                        self.send_json({"error": f"Voice reference file not found: {voice_file}", "success": False}, status_code=404)
                        return
                    tts_engine.tts_to_file(
                        text=text,
                        speaker_wav=speaker_path,
                        language=lang,
                        file_path=out_path
                    )

            elapsed = round(time.time() - t0, 1)
            file_size = os.path.getsize(out_path)

            self.send_json({
                "success": True,
                "filename": out_filename,
                "path": out_path,
                "audio_url": f"/api/audio/{urllib.parse.quote(out_filename)}",
                "elapsed": elapsed,
                "size": file_size
            })
        except Exception as e:
            self.send_json({"error": f"Synthesis error: {e}", "success": False}, status_code=500)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def run():
    global server_instance
    server_address = ("127.0.0.1", PORT)
    server_instance = ThreadedHTTPServer(server_address, XTTSHandler)

    wd = threading.Thread(target=watchdog_loop, daemon=True)
    wd.start()

    # Launch background warm-up of XTTS-v2
    loader = threading.Thread(target=warm_tts_engine, daemon=True)
    loader.start()

    print(f"==================================================")
    print(f"  🎙️ XTTS Studio running at http://127.0.0.1:{PORT}")
    print(f"  📁 Voices Directory: {VOICES_DIR}")
    print(f"  🔊 Output Directory: {OUTPUT_DIR}")
    print(f"  ⚡ Engine:           Warm In-Memory (Background loading...)")
    print(f"  🛡️ Auto-offload:    Enabled on window/app close")
    print(f"==================================================")
    try:
        server_instance.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping XTTS Studio...")
        server_instance.shutdown()

if __name__ == "__main__":
    run()
