"""
Cutter module — uses ffmpeg to cut clips from the source video.

ffmpeg is the industry-standard tool for video/audio processing.
We use Python's subprocess module to call it from our code.

Why not a Python video library?
- ffmpeg is faster and more reliable for cutting.
- It handles every video format imaginable.
- Re-encoding with libx264/aac ensures compatibility everywhere.
"""

import os
import subprocess


OUTPUT_DIR = "clips"


def cut_clips(video_path: str, clips: list[dict], output_dir: str = OUTPUT_DIR) -> list[str]:
    """
    Cut clips from a video file using ffmpeg.

    Args:
        video_path: Path to the source video.
        clips: List of clip dicts with "start" and "end" keys.
        output_dir: Directory to save the cut clips.

    Returns:
        list[str]: Paths to the saved clip files.

    How it works:
        For each clip, we run an ffmpeg command like:

            ffmpeg -y -ss 10.5 -i video.mp4 -t 45.0 -c:v libx264 -c:a aac clip_1.mp4

        Breaking down the flags:
            -y          → Overwrite output file without asking
            -ss 10.5    → Seek to 10.5 seconds (start of clip)
            -i video.mp4 → Input file
            -t 45.0     → Cut for 45 seconds (duration)
            -c:v libx264 → Re-encode video with H.264 codec
            -c:a aac     → Re-encode audio with AAC codec

        Why re-encode instead of -c copy (stream copy)?
            Stream copy (-c copy) is much faster but can produce clips
            that start on the wrong keyframe, causing a few seconds of
            black/frozen video at the start. Re-encoding is slower but
            guarantees frame-perfect cuts.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved_paths = []

    base_name = os.path.splitext(os.path.basename(video_path))[0]

    for i, clip in enumerate(clips):
        start = clip["start"]
        end = clip["end"]
        duration = end - start

        output_filename = f"{base_name}_clip_{i + 1}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        print(f"  Cutting clip {i + 1}/{len(clips)}: {start:.1f}s → {end:.1f}s ({duration:.1f}s)")

        cmd = [
            "ffmpeg",
            "-y",                   # overwrite
            "-ss", str(start),       # seek to start time
            "-i", video_path,        # input file
            "-t", str(duration),     # duration to cut
            "-c:v", "libx264",       # video codec
            "-c:a", "aac",           # audio codec
            "-loglevel", "warning",  # suppress verbose output
            output_path,
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            saved_paths.append(output_path)
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  Error cutting clip {i + 1}: {e.stderr}")
        except FileNotFoundError:
            print("  ❌ ffmpeg not found! Install it: brew install ffmpeg")
            break

    return saved_paths
