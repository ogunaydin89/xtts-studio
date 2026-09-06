# 🎙️ XTTS Studio

> A sleek, high-performance desktop studio for speech synthesis, voice cloning, and YouTube Shorts voiceover production powered by Coqui XTTS v2.

XTTS Studio gives you instantaneous voice synthesis and reference-cloning capabilities with an interface designed specifically for content creators and fast pacing calibration.

---

## ✨ Features

- **🚀 Zero-Dependency Desktop UI**: Built with pure Python 3 standard library + responsive HTML5/CSS3/ES6. No Node.js, no Electron, zero extra dependencies for the interface layer.
- **⚡ Chrome Standalone App Wrapper**: Launches instantly in a distraction-free native desktop window via `google-chrome --app=...` or your preferred browser.
- **🧬 Dynamic Voice Cloning**: Select from preset narrator voices or drag and drop your own 3–6 second `.wav` audio sample to clone any target voice.
- **⏱️ YouTube Shorts Pacing Meter**:
  - Real-time word and character counter.
  - Speech duration calculator calibrated for 9–10s delivery.
  - Visual status badge highlighting the optimal **16–18 word window** for single-pass YouTube Shorts and Reels.
- **🌍 Multilingual Speech**: Supports English, Turkish, German, Spanish, French, Italian, Japanese, Portuguese, Polish, Russian, Arabic, and Chinese.
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
| `XTTS_VENV` | `~/Local Ai Production/venv-xtts` | Path to virtual environment containing `tts` |
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
