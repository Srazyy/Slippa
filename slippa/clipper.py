"""
Clipper module — analyzes transcription to find clip-worthy moments.

This is the "brain" of Slippa. It takes a transcript (list of timed text
segments) and decides which parts of the video would make good clips.

Current approach (MVP — Phase 2):
    Segment-based grouping with scoring:
    1. Group consecutive transcript segments into candidate clips
       (target duration: 30-90 seconds).
    2. Score each candidate based on:
       - Word density (more words = more engaging)
       - Segment count (more segments = more back-and-forth / energy)
    3. Return the top N highest-scoring candidates.

Future improvements:
    - Use a local LLM (via Ollama) to score clip quality.
    - Detect topic boundaries using NLP.
    - Sentiment analysis to find emotional peaks.
"""


# Clip length preferences (in seconds)
MIN_CLIP_DURATION = 15
MAX_CLIP_DURATION = 90
TARGET_CLIP_DURATION = 45

# How many clips to return
MAX_CLIPS = 10


def find_clips(
    segments: list[dict],
    min_duration: float = MIN_CLIP_DURATION,
    max_duration: float = MAX_CLIP_DURATION,
    max_clips: int = MAX_CLIPS,
) -> list[dict]:
    """
    Analyze transcript segments and find the best clips.

    Args:
        segments: List of transcript segments from the transcriber.
                  Each has "start", "end", and "text" keys.
        min_duration: Minimum clip length in seconds.
        max_duration: Maximum clip length in seconds.
        max_clips: Maximum number of clips to return.

    Returns:
        list[dict]: Best clips, each containing:
            - "start": float — clip start time
            - "end": float — clip end time
            - "text": str — combined transcript text
            - "score": float — quality score

    How it works:
        We use a sliding window approach:
        1. Start from the first segment.
        2. Keep adding segments until we hit max_duration.
        3. Score that window (candidate clip).
        4. Slide the window forward by one segment and repeat.
        5. Sort all candidates by score, remove overlapping ones,
           and return the top N.
    """
    if not segments:
        return []

    # Step 1: Generate candidate clips using a sliding window
    candidates = []

    for i in range(len(segments)):
        clip_text_parts = []
        clip_start = segments[i]["start"]
        clip_end = segments[i]["end"]

        for j in range(i, len(segments)):
            clip_end = segments[j]["end"]
            clip_text_parts.append(segments[j]["text"])
            duration = clip_end - clip_start

            # If we've exceeded max duration, stop extending this window
            if duration > max_duration:
                break

            # Only consider clips that meet minimum duration
            if duration >= min_duration:
                combined_text = " ".join(clip_text_parts)
                score = _score_clip(combined_text, duration, j - i + 1)
                candidates.append({
                    "start": clip_start,
                    "end": clip_end,
                    "text": combined_text,
                    "score": score,
                    "segment_count": j - i + 1,
                })

    # Step 2: Sort by score (highest first)
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # Step 3: Remove overlapping clips (greedy — keep highest scored)
    selected = _remove_overlaps(candidates, max_clips)

    # Sort selected clips by start time for logical ordering
    selected.sort(key=lambda c: c["start"])

    return selected


def _score_clip(text: str, duration: float, segment_count: int) -> float:
    """
    Score a candidate clip. Higher score = better clip.

    Scoring factors:
        1. Word density — more words per second = more content/energy.
        2. Segment density — more segments in the duration = more
           back-and-forth, which usually means more engaging content.
        3. Duration sweet spot — clips closer to the target duration
           get a bonus.

    This is intentionally simple for the MVP. We'll improve this later
    with NLP and/or local LLM scoring.
    """
    word_count = len(text.split())

    if duration <= 0:
        return 0.0

    # Words per second (typical speech is ~2.5 words/sec)
    word_density = word_count / duration

    # Segments per second (more = livelier)
    segment_density = segment_count / duration

    # Duration sweet spot bonus: peaks at TARGET_CLIP_DURATION
    duration_diff = abs(duration - TARGET_CLIP_DURATION)
    duration_bonus = max(0, 1.0 - (duration_diff / TARGET_CLIP_DURATION))

    # Combined score
    score = (word_density * 2.0) + (segment_density * 1.5) + (duration_bonus * 1.0)

    return round(score, 3)


def _remove_overlaps(candidates: list[dict], max_clips: int) -> list[dict]:
    """
    Remove overlapping clips, keeping the highest-scored ones.

    This uses a greedy algorithm:
    1. Take the highest-scored clip.
    2. Remove any clip that overlaps with it.
    3. Repeat until we have max_clips or run out of candidates.

    Two clips "overlap" if one starts before the other ends.
    """
    selected = []

    for candidate in candidates:
        if len(selected) >= max_clips:
            break

        # Check if this candidate overlaps with any already-selected clip
        overlaps = False
        for chosen in selected:
            if candidate["start"] < chosen["end"] and candidate["end"] > chosen["start"]:
                overlaps = True
                break

        if not overlaps:
            selected.append(candidate)

    return selected
