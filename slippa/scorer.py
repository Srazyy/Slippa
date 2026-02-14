"""
Scorer module — NLP-powered engagement scoring for clip selection.

Analyzes transcript text to predict how engaging / viral a clip would be.
Uses lightweight libraries (TextBlob + regex) so everything runs locally
with no API keys and no large model downloads.

Scoring dimensions:
    1. Engagement  — questions, calls-to-action, exclamations, hooks
    2. Emotion     — sentiment intensity (strong positive OR negative = good)
    3. Coherence   — topic focus (does the clip stay on one subject?)
    4. Virality    — controversy, surprise, humor, strong opinions

Each dimension scores 0-10, and the final score is a weighted average.
"""

import re
import math
from textblob import TextBlob


# ── Keyword / pattern banks ────────────────────────────────────────────

# Engagement hooks — phrases that grab attention
HOOK_PATTERNS = [
    r"\b(here'?s the thing|the truth is|let me tell you|listen)\b",
    r"\b(you need to|you have to|you should|you must)\b",
    r"\b(number one|first of all|most important)\b",
    r"\b(secret|hack|trick|tip|mistake|problem)\b",
    r"\b(never|always|every single|literally)\b",
    r"\b(crazy|insane|unbelievable|incredible|amazing|mind.?blowing)\b",
    r"\b(broke|blew my mind|changed my life|game.?changer)\b",
    r"\b(don'?t make this mistake|stop doing|warning)\b",
]

# Virality triggers — controversial / emotional / surprising content
VIRAL_PATTERNS = [
    r"\b(controversial|unpopular opinion|hot take|hear me out)\b",
    r"\b(no one talks about|they don'?t want you to know)\b",
    r"\b(plot twist|wait for it|you won'?t believe)\b",
    r"\b(worst|best|biggest|most underrated|overrated)\b",
    r"\b(debate|fight me|disagree|wrong|right)\b",
    r"\b(money|income|salary|million|billion|expensive|free)\b",
    r"\b(fail|success|win|lose|destroy|dominate)\b",
    r"\b(story ?time|so basically|okay so)\b",
]

# Storytelling indicators — narrative structure = more watchable
STORY_PATTERNS = [
    r"\b(so what happened was|long story short|basically)\b",
    r"\b(and then|but then|suddenly|out of nowhere)\b",
    r"\b(turned out|ended up|realized|found out)\b",
    r"\b(i remember|i was|we were|this one time)\b",
    r"\b(beginning|middle|end|finally|eventually)\b",
]

# Call-to-action patterns
CTA_PATTERNS = [
    r"\b(subscribe|like|comment|share|follow|click|check out|link)\b",
    r"\b(let me know|tell me|what do you think|drop a comment)\b",
    r"\b(smash that|hit the|leave a)\b",
]


def score_engagement(
    text: str,
    duration: float,
    segment_count: int,
) -> dict:
    """
    Score a clip's engagement potential using NLP analysis.

    Args:
        text: The transcript text of the clip.
        duration: Clip duration in seconds.
        segment_count: Number of transcript segments in the clip.

    Returns:
        dict with keys:
            - total: float (0-10)
            - engagement: float (0-10)
            - emotion: float (0-10)
            - coherence: float (0-10)
            - virality: float (0-10)
            - label: str — human-readable quality label
            - breakdown: dict — detailed sub-scores for debugging
    """
    if not text or duration <= 0:
        return _empty_score()

    text_lower = text.lower()
    blob = TextBlob(text)
    sentences = blob.sentences or [blob]

    # ── Dimension 1: Engagement ────────────────────────────────────
    engagement, eng_details = _score_engagement_signals(
        text, text_lower, sentences, duration
    )

    # ── Dimension 2: Emotion ───────────────────────────────────────
    emotion, emo_details = _score_emotion(blob, sentences)

    # ── Dimension 3: Coherence ─────────────────────────────────────
    coherence, coh_details = _score_coherence(blob, sentences, duration)

    # ── Dimension 4: Virality ──────────────────────────────────────
    virality, vir_details = _score_virality(text_lower, sentences)

    # ── Duration bonus (same idea as before, but gentler) ──────────
    duration_bonus = _duration_bonus(duration)

    # ── Weighted total ─────────────────────────────────────────────
    total = (
        engagement * 0.30
        + emotion * 0.25
        + coherence * 0.15
        + virality * 0.20
        + duration_bonus * 0.10
    )
    total = round(min(10.0, total), 2)

    label = _label_from_score(total)

    return {
        "total": total,
        "engagement": round(engagement, 2),
        "emotion": round(emotion, 2),
        "coherence": round(coherence, 2),
        "virality": round(virality, 2),
        "label": label,
        "breakdown": {
            "engagement_details": eng_details,
            "emotion_details": emo_details,
            "coherence_details": coh_details,
            "virality_details": vir_details,
            "duration_bonus": round(duration_bonus, 2),
        },
    }


def _empty_score() -> dict:
    """Return a zeroed-out score dict."""
    return {
        "total": 0.0,
        "engagement": 0.0,
        "emotion": 0.0,
        "coherence": 0.0,
        "virality": 0.0,
        "label": "💤 Meh",
        "breakdown": {},
    }


# ── Engagement scoring ─────────────────────────────────────────────────

def _score_engagement_signals(
    text: str,
    text_lower: str,
    sentences,
    duration: float,
) -> tuple[float, dict]:
    """
    Score based on hooks, questions, exclamations, CTAs, and word density.
    """
    # Count pattern matches
    hook_hits = _count_pattern_hits(text_lower, HOOK_PATTERNS)
    cta_hits = _count_pattern_hits(text_lower, CTA_PATTERNS)

    # Question marks → audience engagement
    question_count = text.count("?")

    # Exclamations → energy / excitement
    exclamation_count = text.count("!")

    # Word density (speech rate) — ~2.5 wps is normal, higher = energetic
    word_count = len(text.split())
    wps = word_count / duration if duration > 0 else 0

    # Scoring
    hook_score = min(10.0, hook_hits * 2.0)
    question_score = min(10.0, question_count * 2.5)
    exclamation_score = min(10.0, exclamation_count * 1.5)
    cta_score = min(10.0, cta_hits * 3.0)

    # Word density: sweet spot is 2.5-3.5 wps
    if wps >= 2.5:
        density_score = min(10.0, (wps / 3.0) * 7.0)
    else:
        density_score = max(0.0, (wps / 2.5) * 5.0)

    combined = (
        hook_score * 0.30
        + question_score * 0.20
        + exclamation_score * 0.15
        + cta_score * 0.10
        + density_score * 0.25
    )

    details = {
        "hooks": hook_hits,
        "questions": question_count,
        "exclamations": exclamation_count,
        "ctas": cta_hits,
        "words_per_sec": round(wps, 2),
    }

    return min(10.0, combined), details


# ── Emotion scoring ────────────────────────────────────────────────────

def _score_emotion(blob: TextBlob, sentences) -> tuple[float, dict]:
    """
    Score based on sentiment intensity. Strong feelings = engaging.
    Neutral/bland = boring.
    """
    if not sentences:
        return 0.0, {}

    # Get polarity and subjectivity
    polarity = blob.sentiment.polarity       # -1 to 1
    subjectivity = blob.sentiment.subjectivity  # 0 to 1

    # We care about INTENSITY, not direction
    # Very positive or very negative = engaging
    intensity = abs(polarity)

    # Per-sentence variance — emotional rollercoasters are engaging
    sentence_polarities = [s.sentiment.polarity for s in sentences]
    if len(sentence_polarities) > 1:
        variance = _variance(sentence_polarities)
        swing_bonus = min(3.0, variance * 10.0)
    else:
        swing_bonus = 0.0

    # Subjectivity bonus — opinions are more engaging than facts
    subjectivity_score = subjectivity * 6.0

    # Combined
    emotion_score = (
        intensity * 8.0      # raw emotional intensity
        + swing_bonus         # emotional range
        + subjectivity_score * 0.3  # opinion bonus
    )

    details = {
        "polarity": round(polarity, 3),
        "intensity": round(intensity, 3),
        "subjectivity": round(subjectivity, 3),
        "swing": round(swing_bonus, 2),
    }

    return min(10.0, emotion_score), details


# ── Coherence scoring ──────────────────────────────────────────────────

def _score_coherence(
    blob: TextBlob,
    sentences,
    duration: float,
) -> tuple[float, dict]:
    """
    Score topic focus. A clip that stays on one subject feels complete.
    Rambling text with many unrelated topics scores lower.
    """
    words = [w.lower() for w in blob.words if len(w) > 3]

    if len(words) < 5:
        return 5.0, {"reason": "too_few_words"}

    # Simple approach: measure word repetition as a proxy for topic focus
    # More repeated content words = more focused on one topic
    unique_words = set(words)
    repetition_ratio = 1.0 - (len(unique_words) / len(words))

    # Noun phrase density — more noun phrases = more concrete/focused
    noun_phrases = blob.noun_phrases
    np_density = len(noun_phrases) / max(1, len(sentences))

    # Sentence length consistency — similar sentence lengths = better structure
    if len(sentences) > 1:
        sent_lengths = [len(str(s).split()) for s in sentences]
        avg_len = sum(sent_lengths) / len(sent_lengths)
        length_variance = _variance(sent_lengths)
        consistency = max(0, 1.0 - (length_variance / max(1, avg_len ** 2)))
    else:
        consistency = 0.7

    coherence_score = (
        repetition_ratio * 12.0
        + min(5.0, np_density * 2.0)
        + consistency * 3.0
    )

    details = {
        "repetition_ratio": round(repetition_ratio, 3),
        "noun_phrase_density": round(np_density, 2),
        "consistency": round(consistency, 3),
    }

    return min(10.0, coherence_score), details


# ── Virality scoring ───────────────────────────────────────────────────

def _score_virality(text_lower: str, sentences) -> tuple[float, dict]:
    """
    Score potential virality based on controversial, surprising,
    or emotionally provocative language.
    """
    viral_hits = _count_pattern_hits(text_lower, VIRAL_PATTERNS)
    story_hits = _count_pattern_hits(text_lower, STORY_PATTERNS)

    # Superlatives and absolutes are viral ("the BEST", "NEVER do this")
    superlative_count = len(re.findall(
        r"\b(best|worst|most|least|always|never|every|none)\b",
        text_lower,
    ))

    # Short punchy sentences are more shareable
    punchy_sentences = sum(
        1 for s in sentences if len(str(s).split()) <= 8
    )
    punch_ratio = punchy_sentences / max(1, len(sentences))

    # Numbers / stats make content feel authoritative
    number_count = len(re.findall(r"\b\d+\b", text_lower))

    viral_score = min(10.0, viral_hits * 1.8)
    story_score = min(10.0, story_hits * 2.5)
    superlative_score = min(5.0, superlative_count * 1.0)
    punch_score = punch_ratio * 4.0
    number_score = min(3.0, number_count * 0.5)

    combined = (
        viral_score * 0.35
        + story_score * 0.25
        + superlative_score * 0.15
        + punch_score * 0.15
        + number_score * 0.10
    )

    details = {
        "viral_triggers": viral_hits,
        "story_markers": story_hits,
        "superlatives": superlative_count,
        "punchy_ratio": round(punch_ratio, 2),
        "numbers": number_count,
    }

    return min(10.0, combined), details


# ── Helpers ────────────────────────────────────────────────────────────

def _count_pattern_hits(text: str, patterns: list[str]) -> int:
    """Count total regex matches across all patterns."""
    total = 0
    for pattern in patterns:
        total += len(re.findall(pattern, text, re.IGNORECASE))
    return total


def _variance(values: list[float]) -> float:
    """Calculate variance of a list of numbers."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def _duration_bonus(duration: float, target: float = 45.0) -> float:
    """
    Bonus for clips near the target duration.
    Peaks at target, falls off gently.
    """
    diff = abs(duration - target)
    bonus = max(0, 10.0 - (diff / target) * 10.0)
    return bonus


def _label_from_score(score: float) -> str:
    """Convert a numeric score to a human-readable engagement label."""
    if score >= 7.0:
        return "🔥 Viral"
    elif score >= 5.0:
        return "⭐ Great"
    elif score >= 3.0:
        return "👍 Good"
    else:
        return "💤 Meh"
