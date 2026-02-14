"""
App-wide configuration and settings.

Settings can be changed at runtime via the web UI (/settings).
They persist in a JSON file so they survive restarts.
"""

import os
import json

SETTINGS_FILE = "slippa_settings.json"

# Defaults
DEFAULTS = {
    "whisper_model": "base",
    "min_clip_duration": 15,
    "max_clip_duration": 90,
    "target_clip_duration": 45,
    "max_clips": 10,
    "default_privacy": "private",
    "download_dir": "downloads",
    "clips_dir": "clips",
    "smart_edit": True,
    "gap_threshold": 0.8,
    "output_format": "horizontal",  # "horizontal" | "vertical" | "both"
    "smart_scoring": True,           # NLP-powered clip scoring
}

# Available Whisper models for the settings UI
WHISPER_MODELS = [
    {"value": "tiny", "label": "Tiny", "desc": "Fastest, least accurate (~1 GB RAM)"},
    {"value": "base", "label": "Base", "desc": "Good balance for testing (~1 GB RAM)"},
    {"value": "small", "label": "Small", "desc": "Decent quality (~2 GB RAM)"},
    {"value": "medium", "label": "Medium", "desc": "Good quality (~5 GB RAM)"},
    {"value": "large-v3", "label": "Large v3", "desc": "Best quality (~10 GB RAM)"},
]


def load_settings() -> dict:
    """Load settings from disk, falling back to defaults."""
    settings = DEFAULTS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            settings.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    return settings


def save_settings(settings: dict):
    """Save settings to disk."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get(key: str):
    """Get a single setting value."""
    return load_settings().get(key, DEFAULTS.get(key))
