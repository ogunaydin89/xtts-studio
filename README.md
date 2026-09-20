# 🎙️ XTTS Studio

> A sleek, high-performance desktop studio for speech synthesis, voice cloning, and YouTube Shorts voiceover production powered by Coqui XTTS v2.

XTTS Studio gives you instantaneous voice synthesis and reference-cloning capabilities with an interface designed specifically for content creators and fast pacing calibration.

---

## ✨ Features

- **🚀 Zero-Dependency Server Layer**: The studio backend is pure Python 3 standard library + responsive HTML5/CSS3/ES6. No Node.js, no Electron, no pip dependencies for the interface layer.
- **⚡ Native Qt6 Window**: Launches in a distraction-free isolated `QWebEngineView` desktop window (`window.py`) served from the project's own `.venv` — no Google Chrome dependency. A browser or Chrome app-mode fallback remains in `run.sh` if PyQt6 is unavailable.
- **🔥 Warm In-Memory Engine**: XTTS-v2 is loaded into RAM once at startup in a background thread, so the first synthesis carries no cold-boot penalty and the UI stays responsive while the model warms.
- **🧬 Dynamic Voice Cloning**: Select from preset narrator voices or drag and drop your own 3–6 second `.wav` audio sample to clone any target voice.
- **🎭 58 Built-in Speakers**: XTTS-v2's bundled pretrained speakers (`speakers_xtts.pth`) are exposed directly in the voice picker, so no reference audio is needed to get a usable narrator.
- **⏱️ YouTube Shorts Pacing Meter**:
  - Real-time word and character counter.
  - Speech duration calculator calibrated for 9–10s delivery.
  - Visual status badge highlighting the optimal **16–18 word window** for single-pass YouTube Shorts and Reels.
- **🌍 Multilingual Speech**: English, Turkish, German, Spanish, French, Italian, Japanese, Portuguese, Polish, Russian, and Arabic.
- **🛡️ Hardware Isolation**: Runs strictly on the CPU (e.g. 16-thread Ryzen 7) with discrete GPU/VRAM masking (`CUDA_VISIBLE_DEVICES=""`), keeping 100% of GPU resources free for concurrent image/diffusion workloads.
- **🎧 Built-in Audio Player & History**: Audition voice clips immediately with seek-bar scrubbing (backed by HTTP range requests), and open the output folder directly in Dolphin. Every synthesis is already written to `~/Music/AI_Voice`, so the native window suppresses the redundant in-page download.

---

## 🚀 Quick Start

### 1. Launch Studio
```bash
./run.sh
```

### 2. Manual Server Execution
```bash
python3 app.py
```
Then navigate to `http://127.0.0.1:5222`.

---

## 🛠️ Configuration & Architecture

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| `XTTS_STUDIO_PORT` | `5222` | Port for the XTTS Studio HTTP server |
| `XTTS_VENV` | `./.venv` | Virtualenv containing `TTS` and PyQt6. `app.py` re-execs itself into it automatically if started with the system Python. |
| Output Directory | `~/Music/AI_Voice/` | Destination for synthesized WAV recordings |
| Reference Voices | `./voices/` | Storage for reference speaker audio samples |

---

## 🔒 Local Attack Surface

The server binds to loopback only, and additionally:

- **Paths are contained.** `/static/`, `/api/audio/` and `/api/voice_preview/`
  all resolve through `safe_join()`, which rejects anything landing outside its
  base directory — including percent-encoded traversal (`%2e%2e%2f`).
- **The `Host` header is checked** against `127.0.0.1`/`localhost`/`[::1]` on the
  Studio's own port, so a hostname that merely resolves to `127.0.0.1` (DNS
  rebinding) cannot reach these endpoints.
- **Writes require a same-origin request.** JSON endpoints must carry
  `Content-Type: application/json` — which cannot be sent cross-origin without a
  CORS preflight this server never answers — and any request arriving with
  `Sec-Fetch-Site: cross-site` is refused, which is what protects the
  necessarily-multipart `/api/upload_voice`. Responses carry no
  `Access-Control-Allow-Origin`, so no other page can read them either.
- **Uploads are bounded and typed.** The whole multipart body is parsed in
  memory, so it is capped at 64MB, and only `.wav` / `.mp3` / `.flac` are
  accepted. An unsupported file is rejected outright rather than renamed to
  `.wav`, which used to defer the failure to an opaque XTTS decode error.

---

## 📦 Codeberg Git Setup

```bash
git init
git add .
git commit -m "feat: initial commit of XTTS Studio"
git remote add origin https://codeberg.org/helinesca/xtts-studio.git
git branch -M main
git push -u origin main
```

---

## 📄 License

MIT © [helinesca](https://codeberg.org/helinesca)
