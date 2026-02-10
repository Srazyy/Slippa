"""
Uploader module — uploads clips to YouTube via the YouTube Data API v3.

This module handles:
1. OAuth2 authentication (logging into your Google/YouTube account).
2. Uploading video files with metadata (title, description, tags).

Prerequisites:
    - A Google Cloud project with YouTube Data API v3 enabled.
    - OAuth2 credentials downloaded as 'client_secrets.json'.
    - See: https://developers.google.com/youtube/v3/getting-started

Note: This module is a Phase 4 feature. The initial MVP focuses on
download → transcribe → clip → cut. Upload will be integrated later.
"""

# TODO: Phase 4 — YouTube upload integration
# Will be implemented after the core clipping pipeline is working.
# See the existing uploader.py in the old project for reference.
