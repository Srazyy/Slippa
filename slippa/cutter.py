"""
Cutter module — uses ffmpeg to cut clips from the source video.

Supports two modes:
    1. Simple cut — one continuous ffmpeg cut (original behavior).
    2. Smart cut — cuts multiple sub-segments and concatenates them
       into one seamless clip (removes silence/dead air).

Also supports vertical (9:16) output for YouTube Shorts / TikTok / Reels.
"""

import os
import subprocess
import tempfile


OUTPUT_DIR = "clips"


def cut_clips(
    video_path: str,
    clips: list[dict],
    output_dir: str = OUTPUT_DIR,
    smart_edit: bool = False,
    output_format: str = "horizontal",
) -> list[str]:
    """
    Cut clips from a video file using ffmpeg.

    Args:
        video_path: Path to the source video.
        clips: List of clip dicts with "start", "end", and optionally "sub_segments".
        output_dir: Directory to save the cut clips.
        smart_edit: If True and clip has sub_segments, use concat mode.
        output_format: "horizontal" (original), "vertical" (9:16), or "both".

    Returns:
        list[str]: Paths to the saved clip files.
    """
    os.makedirs(output_dir, exist_ok=True)
    saved_paths = []

    base_name = os.path.splitext(os.path.basename(video_path))[0]

    formats_to_produce = []
    if output_format == "both":
        formats_to_produce = ["horizontal", "vertical"]
    else:
        formats_to_produce = [output_format]

    for i, clip in enumerate(clips):
        for fmt in formats_to_produce:
            suffix = "_vertical" if fmt == "vertical" else ""
            output_filename = f"{base_name}_clip_{i + 1}{suffix}.mp4"
            output_path = os.path.join(output_dir, output_filename)

            sub_segments = clip.get("sub_segments") if smart_edit else None

            if sub_segments and len(sub_segments) > 1:
                # Smart cut: cut each sub-segment → concat
                _smart_cut(video_path, sub_segments, output_path, fmt, i, len(clips))
            else:
                # Simple cut
                start = clip["start"]
                duration = clip["end"] - start
                _simple_cut(video_path, start, duration, output_path, fmt, i, len(clips))

            if os.path.exists(output_path):
                saved_paths.append(output_path)

    return saved_paths


def _build_video_filters(fmt: str) -> list[str]:
    """Build ffmpeg filter flags for the given output format."""
    if fmt == "vertical":
        # Center-crop to 9:16 then scale to 1080x1920
        return ["-vf", "crop=ih*9/16:ih,scale=1080:1920"]
    return []


def _simple_cut(
    video_path: str,
    start: float,
    duration: float,
    output_path: str,
    fmt: str,
    clip_idx: int,
    total_clips: int,
):
    """Cut a single continuous range from the video."""
    print(f"  Cutting clip {clip_idx + 1}/{total_clips}: {start:.1f}s → {start + duration:.1f}s ({duration:.1f}s)")

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        *_build_video_filters(fmt),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-loglevel", "warning",
        output_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Error cutting clip {clip_idx + 1}: {e.stderr}")
    except FileNotFoundError:
        print("  ❌ ffmpeg not found! Install it: brew install ffmpeg")


def _smart_cut(
    video_path: str,
    sub_segments: list[dict],
    output_path: str,
    fmt: str,
    clip_idx: int,
    total_clips: int,
):
    """
    Cut multiple sub-segments and concatenate into one clip.

    1. Cut each sub-segment to a temp file.
    2. Write an ffmpeg concat list.
    3. Concatenate all parts into the final output.
    4. Clean up temp files.
    """
    total_duration = sum(s["end"] - s["start"] for s in sub_segments)
    print(
        f"  Smart-cutting clip {clip_idx + 1}/{total_clips}: "
        f"{len(sub_segments)} segments → {total_duration:.1f}s"
    )

    temp_dir = tempfile.mkdtemp(prefix="slippa_")
    temp_files = []

    try:
        # Step 1: Cut each sub-segment
        for j, seg in enumerate(sub_segments):
            seg_start = seg["start"]
            seg_duration = seg["end"] - seg_start
            temp_path = os.path.join(temp_dir, f"part_{j:03d}.mp4")

            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(seg_start),
                "-i", video_path,
                "-t", str(seg_duration),
                *_build_video_filters(fmt),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-loglevel", "warning",
                temp_path,
            ]

            subprocess.run(cmd, check=True, capture_output=True, text=True)
            temp_files.append(temp_path)

        # Step 2: Write concat list
        concat_list_path = os.path.join(temp_dir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for temp_path in temp_files:
                f.write(f"file '{temp_path}'\n")

        # Step 3: Concatenate
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",
            "-loglevel", "warning",
            output_path,
        ]

        subprocess.run(concat_cmd, check=True, capture_output=True, text=True)

    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Error smart-cutting clip {clip_idx + 1}: {e.stderr}")
    except FileNotFoundError:
        print("  ❌ ffmpeg not found! Install it: brew install ffmpeg")
    finally:
        # Step 4: Clean up temp files
        for temp_path in temp_files:
            try:
                os.remove(temp_path)
            except OSError:
                pass
        try:
            os.remove(os.path.join(temp_dir, "concat.txt"))
            os.rmdir(temp_dir)
        except OSError:
            pass
