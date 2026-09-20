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
- **🎧 Built-in Audio Player & History**: Audition voice clips immediately with waveform scrubbing, one-click WAV download, and direct integration with Dolphin file manager.

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
