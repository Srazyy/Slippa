"""
Tests for the smart scorer module.

Validates that NLP scoring correctly differentiates between
engaging, emotional, viral content vs. bland filler content.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slippa.scorer import score_engagement, _label_from_score


# ── Test data ──────────────────────────────────────────────────────────

ENGAGING_TEXT = """
Here's the thing — you need to stop doing this one thing right now.
Number one mistake people make? They never actually test their code.
Let me tell you, this is a game changer. Are you ready? Listen up!
This hack changed my life and it will change yours too.
"""

BLAND_TEXT = """
The process involves several steps. First we do this. Then we do that.
After completing the previous step, we move on to the next step.
The system processes the data according to the specifications.
Results are then stored in the database for later retrieval.
"""

EMOTIONAL_TEXT = """
I was absolutely devastated when I found out. It was the worst day
of my life! I've never felt so betrayed, so heartbroken. But then,
something incredible happened — it was the most amazing surprise ever!
I couldn't believe it! I went from crying to laughing in seconds!
"""

NEUTRAL_TEXT = """
The temperature today is approximately twenty degrees. The meeting
is scheduled for three o'clock. Please review the attached document
and provide your feedback by end of business day Friday.
"""

VIRAL_TEXT = """
Unpopular opinion: this is the worst advice ever and no one talks
about it. Plot twist — they don't want you to know this secret.
Here's my hot take: the best way to make money is completely wrong.
Story time: so basically what happened was unbelievable. Fight me!
"""

BORING_TEXT = """
Item one is completed. Item two is in progress. Item three will be
addressed next week. The committee reviewed the findings and approved
the recommendations as presented in the quarterly report summary.
"""


def test_engaging_beats_bland():
    """Engaging content (hooks, questions, CTAs) should score higher."""
    engaging = score_engagement(ENGAGING_TEXT, 30.0, 5)
    bland = score_engagement(BLAND_TEXT, 30.0, 5)

    print(f"  Engaging: {engaging['total']:.2f} ({engaging['label']})")
    print(f"  Bland:    {bland['total']:.2f} ({bland['label']})")

    assert engaging["total"] > bland["total"], (
        f"Engaging ({engaging['total']}) should beat bland ({bland['total']})"
    )
    assert engaging["engagement"] > bland["engagement"]


def test_emotional_beats_neutral():
    """Emotionally intense content should score higher on emotion."""
    emotional = score_engagement(EMOTIONAL_TEXT, 30.0, 4)
    neutral = score_engagement(NEUTRAL_TEXT, 30.0, 4)

    print(f"  Emotional: {emotional['total']:.2f} (emotion={emotional['emotion']:.2f})")
    print(f"  Neutral:   {neutral['total']:.2f} (emotion={neutral['emotion']:.2f})")

    assert emotional["emotion"] > neutral["emotion"], (
        f"Emotional ({emotional['emotion']}) should beat neutral ({neutral['emotion']})"
    )


def test_viral_beats_boring():
    """Content with viral triggers should score higher on virality."""
    viral = score_engagement(VIRAL_TEXT, 30.0, 5)
    boring = score_engagement(BORING_TEXT, 30.0, 5)

    print(f"  Viral:  {viral['total']:.2f} (virality={viral['virality']:.2f})")
    print(f"  Boring: {boring['total']:.2f} (virality={boring['virality']:.2f})")

    assert viral["virality"] > boring["virality"], (
        f"Viral ({viral['virality']}) should beat boring ({boring['virality']})"
    )


def test_score_structure():
    """Score dict should have all required keys."""
    result = score_engagement("Test text for structure check.", 10.0, 1)

    assert "total" in result
    assert "engagement" in result
    assert "emotion" in result
    assert "coherence" in result
    assert "virality" in result
    assert "label" in result
    assert "breakdown" in result
    assert 0 <= result["total"] <= 10
    print(f"  Structure OK: {result['label']}, total={result['total']}")


def test_empty_input():
    """Empty or zero-duration input should return zero scores."""
    empty = score_engagement("", 10.0, 1)
    assert empty["total"] == 0.0
    assert empty["label"] == "💤 Meh"

    zero_dur = score_engagement("Some text", 0.0, 1)
    assert zero_dur["total"] == 0.0
    print("  Empty inputs handled correctly")


def test_labels():
    """Label thresholds should be correct."""
    assert _label_from_score(8.0) == "🔥 Viral"
    assert _label_from_score(6.0) == "⭐ Great"
    assert _label_from_score(4.0) == "👍 Good"
    assert _label_from_score(1.0) == "💤 Meh"
    print("  Label thresholds OK")


def test_clipper_integration():
    """Test that find_clips works with smart scoring enabled."""
    from slippa.clipper import find_clips

    # Simulate a simple transcript
    segments = [
        {"start": 0.0, "end": 10.0, "text": "Here's the thing, this is amazing!", "words": []},
        {"start": 10.0, "end": 20.0, "text": "You need to hear this incredible secret!", "words": []},
        {"start": 20.0, "end": 30.0, "text": "Number one mistake people make is this.", "words": []},
        {"start": 30.0, "end": 40.0, "text": "Let me tell you why it's a game changer.", "words": []},
    ]

    clips = find_clips(
        segments,
        min_duration=15,
        max_duration=45,
        max_clips=3,
        smart_scoring=True,
    )

    assert len(clips) > 0, "Should find at least one clip"
    for clip in clips:
        assert "label" in clip, "Clip should have a label"
        assert "score_breakdown" in clip, "Clip should have score_breakdown"
        assert 0 <= clip["score"] <= 10, f"Score {clip['score']} should be 0-10"
        print(f"  Clip {clip['start']:.0f}s-{clip['end']:.0f}s: {clip['score']:.2f} ({clip['label']})")

    # Test legacy mode too
    legacy_clips = find_clips(
        segments,
        min_duration=15,
        max_duration=45,
        max_clips=3,
        smart_scoring=False,
    )
    assert len(legacy_clips) > 0, "Legacy should also find clips"
    assert legacy_clips[0]["label"] == "—", "Legacy clips should have '—' label"
    print(f"  Legacy mode OK: {len(legacy_clips)} clips")


if __name__ == "__main__":
    tests = [
        ("Engaging beats Bland", test_engaging_beats_bland),
        ("Emotional beats Neutral", test_emotional_beats_neutral),
        ("Viral beats Boring", test_viral_beats_boring),
        ("Score Structure", test_score_structure),
        ("Empty Input", test_empty_input),
        ("Labels", test_labels),
        ("Clipper Integration", test_clipper_integration),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            print(f"\n🧪 {name}:")
            test_fn()
            print(f"  ✅ PASSED")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed.")
