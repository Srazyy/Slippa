# ✂️ Slippa

**AI-powered YouTube clip generator — runs 100% locally.**

Drop a YouTube link, get clips. No paid APIs, no cloud, no limits.

![Dashboard](https://img.shields.io/badge/UI-Dark%20Glassmorphism-8b5cf6)
![Python](https://img.shields.io/badge/Python-3.10+-3776ab)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- 🎬 **Download** — Grab any YouTube video via `yt-dlp`
- 🎤 **Transcribe** — Local speech-to-text via `faster-whisper` (no API keys)
- 🧠 **Detect Clips** — Sliding-window analysis finds the most engaging moments
- ✂️ **Cut** — Frame-perfect re-encoding via `ffmpeg`
- 📤 **Upload** — Optional YouTube upload with OAuth2
- 📊 **Batch** — Process multiple videos in one go
- ⚙️ **Settings** — Whisper model, clip duration, max clips — all configurable
- 📜 **History** — Track all processed jobs

## Quick Start

```bash
# Clone
git clone https://github.com/Srazyy/Slippa.git
cd Slippa

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python -m slippa          # Web UI at http://localhost:5000
python -m slippa --cli    # CLI mode
```

## Prerequisites

- Python 3.10+
- ffmpeg (`brew install ffmpeg`)
- ~1 GB disk for Whisper model (auto-downloads on first run)

## Pages

| Page | Description |
|------|-------------|
| **Home** | Paste a YouTube URL → generate clips |
| **Batch** | Process multiple URLs at once |
| **History** | See all past jobs with status |
| **Settings** | Whisper model, durations, max clips, privacy |

## YouTube Upload (Optional)

To upload clips directly to YouTube:

1. Follow [docs/YOUTUBE_SETUP.md](docs/YOUTUBE_SETUP.md) to get credentials
2. Place `client_secrets.json` in the project root
3. Click "📤 YouTube" on any clip → authorize → done

## Tech Stack

- **yt-dlp** — video download
- **faster-whisper** — local speech-to-text
- **ffmpeg** — video cutting
- **Flask** — web UI
- **Google API** — YouTube upload (optional)

## Project Structure

```
Slippa/
├── slippa/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   ├── web.py           # Flask app (17 routes)
│   ├── downloader.py    # yt-dlp wrapper
│   ├── transcriber.py   # faster-whisper wrapper
│   ├── clipper.py       # Clip detection algorithm
│   ├── cutter.py        # ffmpeg clip cutting
│   └── uploader.py      # YouTube upload + OAuth2
├── config/
│   └── settings.py      # Persistent JSON settings
├── templates/           # Jinja2 HTML templates
├── static/              # CSS styles
├── docs/                # Setup guides
└── requirements.txt
```

## License

MIT
