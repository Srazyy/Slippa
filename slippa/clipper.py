"""
Clipper module — analyzes transcription to find clip-worthy moments.

This is the "brain" of Slippa. It takes a transcript (list of timed text
segments) and decides which parts of the video would make good clips.

Smart scoring (Phase 4):
    NLP-powered clip selection using the scorer module:
    1. Group consecutive transcript segments into candidate clips.
    2. Score each candidate using engagement, emotion, coherence,
       and virality analysis (via scorer.py).
    3. Return the top N highest-scoring candidates with labels.

    Falls back to legacy word-density scoring if smart_scoring=False.

Smart editing (Phase 3):
    When enabled, each clip is further refined:
    - Word-level timestamps identify gaps (silence > threshold).
    - The clip is split into talk-only sub-segments.
    - The cutter merges these sub-segments into a single tight clip.
"""

from slippa.scorer import score_engagement


# Clip length preferences (in seconds)
MIN_CLIP_DURATION = 15
MAX_CLIP_DURATION = 90
TARGET_CLIP_DURATION = 45

# How many clips to return
MAX_CLIPS = 10

# Smart editing defaults
DEFAULT_GAP_THRESHOLD = 0.8  # seconds of silence to remove


def find_clips(
    segments: list[dict],
    min_duration: float = MIN_CLIP_DURATION,
    max_duration: float = MAX_CLIP_DURATION,
    max_clips: int = MAX_CLIPS,
    smart_edit: bool = False,
    gap_threshold: float = DEFAULT_GAP_THRESHOLD,
    smart_scoring: bool = True,
) -> list[dict]:
    """
    Analyze transcript segments and find the best clips.

    Args:
        segments: List of transcript segments from the transcriber.
                  Each has "start", "end", "text", and optionally "words" keys.
        min_duration: Minimum clip length in seconds.
        max_duration: Maximum clip length in seconds.
        max_clips: Maximum number of clips to return.
        smart_edit: If True, compute sub-segments that skip silence.
        gap_threshold: Minimum gap (seconds) between words to consider as silence.
        smart_scoring: If True, use NLP-powered scoring. Otherwise use legacy.

    Returns:
        list[dict]: Best clips, each containing:
            - "start": float — clip start time
            - "end": float — clip end time
            - "text": str — combined transcript text
            - "score": float — quality score (0-10 if smart, raw if legacy)
            - "label": str — engagement label (only if smart_scoring)
            - "score_breakdown": dict — detailed sub-scores (only if smart_scoring)
            - "sub_segments": list[dict] — (only if smart_edit) talk-only ranges
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
                seg_count = j - i + 1

                if smart_scoring:
                    score_result = score_engagement(
                        combined_text, duration, seg_count
                    )
                    candidates.append({
                        "start": clip_start,
                        "end": clip_end,
                        "text": combined_text,
                        "score": score_result["total"],
                        "label": score_result["label"],
                        "score_breakdown": {
                            "engagement": score_result["engagement"],
                            "emotion": score_result["emotion"],
                            "coherence": score_result["coherence"],
                            "virality": score_result["virality"],
                        },
                        "segment_count": seg_count,
                        "_seg_range": (i, j),
                    })
                else:
                    score = _score_clip_legacy(
                        combined_text, duration, seg_count
                    )
                    candidates.append({
                        "start": clip_start,
                        "end": clip_end,
                        "text": combined_text,
                        "score": score,
                        "label": "—",
                        "score_breakdown": {},
                        "segment_count": seg_count,
                        "_seg_range": (i, j),
                    })

    # Step 2: Sort by score (highest first)
    candidates.sort(key=lambda c: c["score"], reverse=True)

    # Step 3: Remove overlapping clips (greedy — keep highest scored)
    selected = _remove_overlaps(candidates, max_clips)

    # Step 4: Smart editing — build sub-segments that skip silence
    if smart_edit:
        for clip in selected:
            seg_start, seg_end = clip["_seg_range"]
            clip_segments = segments[seg_start:seg_end + 1]
            clip["sub_segments"] = _build_smart_segments(
                clip_segments, gap_threshold
            )

    # Clean up internal keys
    for clip in selected:
        clip.pop("_seg_range", None)

    # Sort selected clips by start time for logical ordering
    selected.sort(key=lambda c: c["start"])

    return selected


def _build_smart_segments(
    segments: list[dict],
    gap_threshold: float,
) -> list[dict]:
    """
    Analyze word-level timestamps and produce talk-only sub-segments.

    Collects all words from the given segments, then walks through them:
    - If the gap between one word ending and the next starting exceeds
      gap_threshold, a new sub-segment begins.
    - Returns a list of {start, end} dicts representing continuous speech ranges.

    Falls back to one sub-segment spanning the full range if no word data exists.
    """
    # Gather all words across segments
    all_words = []
    for seg in segments:
        all_words.extend(seg.get("words", []))

    if not all_words:
        # No word data → fall back to a single continuous segment
        return [{"start": segments[0]["start"], "end": segments[-1]["end"]}]

    sub_segments = []
    current_start = all_words[0]["start"]
    current_end = all_words[0]["end"]

    for word in all_words[1:]:
        gap = word["start"] - current_end
        if gap > gap_threshold:
            # Close current sub-segment, start a new one
            sub_segments.append({"start": current_start, "end": current_end})
            current_start = word["start"]
        current_end = word["end"]

    # Close the last sub-segment
    sub_segments.append({"start": current_start, "end": current_end})

    return sub_segments


def _score_clip_legacy(text: str, duration: float, segment_count: int) -> float:
    """
    Legacy scoring — simple word/segment density.
    Kept as a fallback when smart_scoring is disabled.
    """
    word_count = len(text.split())

    if duration <= 0:
        return 0.0

    word_density = word_count / duration
    segment_density = segment_count / duration

    duration_diff = abs(duration - TARGET_CLIP_DURATION)
    duration_bonus = max(0, 1.0 - (duration_diff / TARGET_CLIP_DURATION))

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

