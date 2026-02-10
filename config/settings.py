"""
App-wide configuration and settings.
"""

import os

# Directories
DOWNLOAD_DIR = os.environ.get("SLIPPA_DOWNLOAD_DIR", "downloads")
CLIPS_DIR = os.environ.get("SLIPPA_CLIPS_DIR", "clips")

# Whisper settings
WHISPER_MODEL = os.environ.get("SLIPPA_WHISPER_MODEL", "base")

# Clip detection settings
MIN_CLIP_DURATION = int(os.environ.get("SLIPPA_MIN_CLIP_DURATION", 15))
MAX_CLIP_DURATION = int(os.environ.get("SLIPPA_MAX_CLIP_DURATION", 90))
MAX_CLIPS = int(os.environ.get("SLIPPA_MAX_CLIPS", 10))
