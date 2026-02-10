"""
Downloader module — downloads videos from YouTube using yt-dlp.

Why yt-dlp?
- It's the most actively maintained YouTube downloader.
- Supports playlists, age-restricted videos, and many sites beyond YouTube.
- Returns metadata (title, duration, etc.) which we'll use later.
"""

import os
import yt_dlp


# Where downloaded videos are saved
DOWNLOAD_DIR = "downloads"


def download_video(url: str, output_dir: str = DOWNLOAD_DIR) -> str:
    """
    Download a video from a YouTube URL.

    Args:
        url: YouTube video URL (e.g., https://www.youtube.com/watch?v=...)
        output_dir: Directory to save the downloaded video.

    Returns:
        str: Path to the downloaded video file.

    How it works:
        1. We configure yt-dlp with options:
           - 'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
              → Downloads the best quality MP4 video + M4A audio and merges them.
              → Falls back to best single MP4 if separate streams aren't available.
           - 'outtmpl': sets the output filename template.
           - 'merge_output_format': ensures final output is mp4.
        2. yt-dlp handles all the complexity of YouTube's streaming formats,
           downloading, and merging audio+video.
        3. We return the path to the final merged file.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Output filename template: saves as "Video Title.mp4"
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # extract_info downloads the video and returns metadata
        info = ydl.extract_info(url, download=True)

        # Build the actual output path from the metadata
        filename = ydl.prepare_filename(info)

        # Ensure it ends with .mp4 (yt-dlp might have merged formats)
        if not filename.endswith(".mp4"):
            filename = os.path.splitext(filename)[0] + ".mp4"

    return filename
