# 🎬 Slippa

**AI-powered YouTube clip generator that runs 100% locally.**

Slippa takes a YouTube link (or local video file), automatically finds the most engaging moments using local AI, cuts them into clips, and optionally uploads them back to YouTube — all without any paid APIs or cloud dependencies.

## ✨ Features (Planned)

- 📥 **Download** videos from YouTube via `yt-dlp`
- 🎤 **Transcribe** audio locally using OpenAI Whisper
- 🧠 **Detect** the best clip-worthy moments from the transcript
- ✂️ **Cut** clips using `ffmpeg`
- 📤 **Upload** clips to YouTube via the YouTube Data API
- 🔄 **Automate** batch processing and scheduling
- 🖥️ **Web UI** dashboard for managing everything

## 🛠️ Tech Stack

| Component | Tool |
|---|---|
| Video Download | `yt-dlp` |
| Transcription | `faster-whisper` (local, free) |
| Clip Detection | Custom transcript analysis |
| Video Cutting | `ffmpeg` |
| YouTube Upload | YouTube Data API v3 |
| Web UI | Flask |
| Language | Python 3.10+ |

## 📦 Prerequisites

- **Python 3.10+**
- **ffmpeg** installed and available in your PATH
  ```bash
  # macOS
  brew install ffmpeg
  
  # Ubuntu/Debian
  sudo apt install ffmpeg
  ```

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/Srazyy/Slippa.git
cd Slippa

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Slippa
python -m slippa
```

## 📁 Project Structure

```
Slippa/
├── slippa/                 # Main package
│   ├── __init__.py
│   ├── __main__.py         # Entry point (python -m slippa)
│   ├── downloader.py       # YouTube video downloader
│   ├── transcriber.py      # Local Whisper transcription
│   ├── clipper.py          # Clip detection logic
│   ├── cutter.py           # ffmpeg video cutting
│   └── uploader.py         # YouTube upload
├── config/
│   └── settings.py         # App configuration
├── tests/                  # Unit tests
├── requirements.txt
├── .gitignore
└── README.md
```

## 🗺️ Roadmap

- [x] Phase 0: Project setup
- [ ] Phase 1: Download + Transcribe
- [ ] Phase 2: Clip detection + Cutting
- [ ] Phase 3: Web UI
- [ ] Phase 4: YouTube Upload integration
- [ ] Phase 5: Automation + Polish

## 📄 License

MIT

## 🤝 Contributing

This is a learning project. Contributions and suggestions are welcome!
