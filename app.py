#!/usr/bin/env python3
"""
XTTS Studio - Desktop Voice Synthesis & Cloning Studio
Lightweight Python server managing isolated Coqui XTTS v2 generation on CPU.
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

PORT = int(os.environ.get("XTTS_STUDIO_PORT", 5222))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
OUTPUT_DIR = os.path.expanduser("~/Music/AI_Voice")

# Default XTTS environment path
DEFAULT_VENV = os.path.expanduser("~/Local Ai Production/venv-xtts")
VENV_DIR = os.environ.get("XTTS_VENV", DEFAULT_VENV)

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

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

        if path == "/api/synthesize":
            self.handle_api_synthesize()
        elif path == "/api/upload_voice":
            self.handle_upload_voice()
        elif path == "/api/open_folder":
            self.handle_open_folder()
        else:
            self.send_error(404, "Not Found")

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
                # Basic range support for audio seeking
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
        tts_bin = os.path.join(VENV_DIR, "bin", "tts")
        is_ready = os.path.isfile(tts_bin) and os.access(tts_bin, os.X_OK)

        voices = [f for f in os.listdir(VOICES_DIR) if f.lower().endswith((".wav", ".mp3", ".flac"))]
        
        # Get system RAM info
        ram_info = {"total_gb": 16, "free_gb": 8}
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            for line in lines:
                if line.startswith("MemTotal:"):
                    ram_info["total_gb"] = round(int(line.split()[1]) / (1024 * 1024), 1)
                elif line.startswith("MemAvailable:"):
                    ram_info["free_gb"] = round(int(line.split()[1]) / (1024 * 1024), 1)
        except Exception:
            pass

        self.send_json({
            "ready": is_ready,
            "engine": "Coqui XTTS v2 (CPU Isolated)",
            "venv_path": VENV_DIR,
            "voices_count": len(voices),
            "ram": ram_info,
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
        self.send_json({"voices": voice_files})

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

        # Simple multipart reader for wav file
        try:
            boundary = content_type.split("boundary=")[1].encode()
            length = int(self.headers.get("Content-Length", 0))
            raw_data = self.rfile.read(length)
            
            parts = raw_data.split(b"--" + boundary)
            for part in parts:
                if b'filename="' in part:
                    header, file_bytes = part.split(b"\r\n\r\n", 1)
                    file_bytes = file_bytes.rstrip(b"\r\n--")
                    header_str = header.decode("utf-8", errors="ignore")
                    
                    filename = "custom_voice.wav"
                    for h_line in header_str.split("\r\n"):
                        if "filename=" in h_line:
                            filename = h_line.split('filename="')[1].split('"')[0]
                    
                    # Sanitize filename
                    safe_name = os.path.basename(filename).replace(" ", "_")
                    if not safe_name.lower().endswith(".wav"):
                        safe_name += ".wav"
                    
                    dest_path = os.path.join(VOICES_DIR, safe_name)
                    with open(dest_path, "wb") as f:
                        f.write(file_bytes)
                    
                    self.send_json({"success": True, "name": safe_name})
                    return

            self.send_json({"error": "No file content found"}, status_code=400)
        except Exception as e:
            self.send_json({"error": str(e)}, status_code=500)

    def handle_api_synthesize(self):
        payload = self.read_json_body()
        text = payload.get("text", "").strip()
        voice_file = payload.get("voice", "narrator_default.wav")
        lang = payload.get("language", "en")
        speed = float(payload.get("speed", 1.0))

        if not text:
            self.send_json({"error": "Text is required"}, status_code=400)
            return

        tts_bin = os.path.join(VENV_DIR, "bin", "tts")
        if not os.path.isfile(tts_bin):
            self.send_json({"error": f"TTS binary not found at {tts_bin}"}, status_code=500)
            return

        speaker_path = os.path.join(VOICES_DIR, voice_file)
        if not os.path.isfile(speaker_path):
            self.send_json({"error": f"Voice reference not found: {voice_file}"}, status_code=404)
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_filename = f"Voice_{timestamp}_{lang}.wav"
        out_path = os.path.join(OUTPUT_DIR, out_filename)

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = ""
        env["ROCR_VISIBLE_DEVICES"] = ""
        env["HIP_VISIBLE_DEVICES"] = ""
        env["COQUI_TOS_AGREED"] = "1"

        cmd = [
            tts_bin,
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--text", text,
            "--out_path", out_path,
            "--language_idx", lang,
            "--speaker_wav", speaker_path
        ]

        t0 = time.time()
        try:
            proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
            if proc.returncode != 0:
                self.send_json({
                    "error": f"Synthesis failed (code {proc.returncode}): {proc.stderr[:400]}",
                    "success": False
                }, status_code=500)
                return

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
        except subprocess.TimeoutExpired:
            self.send_json({"error": "Synthesis timed out after 120 seconds", "success": False}, status_code=504)
        except Exception as e:
            self.send_json({"error": str(e), "success": False}, status_code=500)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def run():
    server_address = ("127.0.0.1", PORT)
    httpd = ThreadedHTTPServer(server_address, XTTSHandler)
    print(f"==================================================")
    print(f"  🎙️ XTTS Studio running at http://127.0.0.1:{PORT}")
    print(f"  📁 Voices Directory: {VOICES_DIR}")
    print(f"  🔊 Output Directory: {OUTPUT_DIR}")
    print(f"  🐍 XTTS Virtualenv:  {VENV_DIR}")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping XTTS Studio...")
        httpd.shutdown()

if __name__ == "__main__":
    run()
