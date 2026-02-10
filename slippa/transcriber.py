"""
Transcriber module — converts video/audio speech to text using Whisper.

We use `faster-whisper` instead of OpenAI's original `whisper` because:
- It's 4x faster (uses CTranslate2 under the hood).
- Uses less memory.
- Produces identical results.
- Runs 100% locally — no API keys, no internet, no cost.

The transcription output includes word-level timestamps, which we use
in the clipper module to find good clip boundaries.
"""

from faster_whisper import WhisperModel


# Model sizes (bigger = more accurate but slower):
#   "tiny"    — fastest, least accurate (~1GB RAM)
#   "base"    — good balance for testing (~1GB RAM)
#   "small"   — decent quality (~2GB RAM)
#   "medium"  — good quality (~5GB RAM)
#   "large-v3"— best quality (~10GB RAM)
DEFAULT_MODEL_SIZE = "base"


def transcribe_audio(
    video_path: str,
    model_size: str = DEFAULT_MODEL_SIZE,
) -> list[dict]:
    """
    Transcribe speech from a video/audio file.

    Args:
        video_path: Path to the video or audio file.
        model_size: Whisper model size to use.

    Returns:
        list[dict]: A list of transcript segments, each containing:
            - "start": float — start time in seconds
            - "end": float — end time in seconds
            - "text": str — the spoken text in this segment

    How it works:
        1. WhisperModel loads the specified model into memory.
           - On first run, it downloads the model (~150MB for 'base').
           - On subsequent runs, it uses the cached model.
           - 'compute_type="int8"' uses quantization to reduce memory usage.

        2. model.transcribe() processes the audio:
           - Whisper internally extracts audio from the video file.
           - It uses a transformer neural network to convert speech → text.
           - It returns segments with timestamps.

        3. We convert the segments into simple dictionaries for easy use
           in the rest of the pipeline.
    """
    print(f"  Loading Whisper model: {model_size}")
    model = WhisperModel(model_size, compute_type="int8")

    print("  Transcribing...")
    segments_generator, info = model.transcribe(
        video_path,
        beam_size=5,          # Higher = more accurate, slower
        vad_filter=True,      # Voice Activity Detection — skips silent parts
    )

    print(f"  Detected language: {info.language} (confidence: {info.language_probability:.0%})")

    # Convert generator to list of dicts
    segments = []
    for segment in segments_generator:
        segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        })

    return segments
