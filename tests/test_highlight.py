"""Unit tests for transcript highlight-injection logic.

Tests _first_sentence, _mark_fragment, and _inject_mark — the three
pure helper functions that power the yellow-highlight feature across
synthesis review, interview detail, and the transcript drawer.
"""
import html as _html

import pytest

# conftest.py has already mocked google.generativeai before this runs.
from cont_synth.state import (
    _MARK_CLOSE,
    _MARK_OPEN,
    _first_sentence,
    _inject_mark,
    _mark_fragment,
)

OPEN = _MARK_OPEN
CLOSE = _MARK_CLOSE


# ---------------------------------------------------------------------------
# _first_sentence
# ---------------------------------------------------------------------------

class TestFirstSentence:
    def test_ellipsis_split_returns_first_part(self):
        text = "This is the first part... and this continues somewhere else"
        assert _first_sentence(text) == "This is the first part"

    def test_ellipsis_in_first_10_chars_ignored(self):
        # Ellipsis at position 0 should NOT cause a split
        text = "...starts here and this is the full rest of the sentence without split"
        # No sentence boundary either → full text returned
        result = _first_sentence(text)
        assert result == text

    def test_sentence_boundary_period(self):
        text = "This is a complete sentence. And this is another one."
        assert _first_sentence(text) == "This is a complete sentence."

    def test_sentence_boundary_question_mark(self):
        text = "Is this really working? I hope so indeed."
        assert _first_sentence(text) == "Is this really working?"

    def test_sentence_boundary_exclamation(self):
        text = "This is amazing! Great features right here."
        assert _first_sentence(text) == "This is amazing!"

    def test_sentence_boundary_too_early_ignored(self):
        # "Yes." ends at position 3, which is < 10 — should not split there
        text = "Yes. This is a much longer sentence that should be kept together."
        result = _first_sentence(text)
        # The boundary at pos 3 is ignored; next boundary is further ahead
        assert result.startswith("Yes.")
        assert len(result) > 4  # More than just "Yes."

    def test_no_boundary_returns_full_text(self):
        text = "no punctuation here just a continuous chunk of text"
        assert _first_sentence(text) == text

    def test_empty_string(self):
        assert _first_sentence("") == ""

    def test_ellipsis_preferred_over_period(self):
        """Ellipsis check happens before sentence-boundary check.

        The ellipsis must start after position 10 for the guard to fire.
        'First long part here' is 20 chars so the condition is satisfied.
        """
        text = "First long part here... second part. third part"
        result = _first_sentence(text)
        assert result == "First long part here"

    def test_four_dot_ellipsis(self):
        text = "Starting sentence.... then the rest continues here"
        result = _first_sentence(text)
        assert result == "Starting sentence"


# ---------------------------------------------------------------------------
# _mark_fragment
# ---------------------------------------------------------------------------

class TestMarkFragment:
    def test_exact_match_single_word(self):
        text = "Hello world, how are you?"
        result = _mark_fragment(text, "world")
        assert result == f"Hello {OPEN}world{CLOSE}, how are you?"

    def test_exact_match_multi_word(self):
        text = "The quick brown fox jumps over the lazy dog"
        result = _mark_fragment(text, "brown fox")
        assert result == f"The quick {OPEN}brown fox{CLOSE} jumps over the lazy dog"

    def test_empty_fragment_returns_none(self):
        assert _mark_fragment("some text", "") is None

    def test_whitespace_only_fragment_returns_none(self):
        assert _mark_fragment("some text", "   ") is None
        assert _mark_fragment("some text", "\t\n") is None

    def test_fragment_not_in_text_returns_none(self):
        assert _mark_fragment("Hello world", "missing phrase entirely") is None

    def test_multi_word_flexible_whitespace_tab(self):
        """Flexible regex matches words separated by tab."""
        text = "Hello\tworld"
        result = _mark_fragment(text, "Hello world")
        assert result is not None
        assert OPEN in result and CLOSE in result

    def test_multi_word_flexible_whitespace_newline(self):
        """Flexible regex matches words separated by newline."""
        text = "users\nstruggle\nwith"
        result = _mark_fragment(text, "users struggle with")
        assert result is not None
        assert OPEN in result

    def test_marks_first_occurrence_only(self):
        text = "cat and cat and cat"
        result = _mark_fragment(text, "cat")
        assert result is not None
        assert result.count(OPEN) == 1

    def test_fragment_at_start(self):
        result = _mark_fragment("Hello world", "Hello")
        assert result == f"{OPEN}Hello{CLOSE} world"

    def test_fragment_at_end(self):
        result = _mark_fragment("Hello world", "world")
        assert result == f"Hello {OPEN}world{CLOSE}"

    def test_full_text_as_fragment(self):
        text = "exact match entire line"
        result = _mark_fragment(text, text)
        assert result == f"{OPEN}exact match entire line{CLOSE}"

    def test_single_word_no_flexible_path(self):
        """Single word can't use flexible-whitespace path (needs ≥2 words)."""
        result = _mark_fragment("find nothing", "missing")
        assert result is None


# ---------------------------------------------------------------------------
# _inject_mark
# ---------------------------------------------------------------------------

class TestInjectMark:
    def test_pass1_exact_match(self):
        escaped = _html.escape("This is a test quote in the transcript.")
        quote = _html.escape("test quote")
        result = _inject_mark(escaped, quote)
        assert OPEN in result
        assert "test quote" in result

    def test_empty_quote_returns_unchanged(self):
        text = "Some transcript content"
        assert _inject_mark(text, "") == text

    def test_whitespace_quote_returns_unchanged(self):
        text = "Some transcript content"
        assert _inject_mark(text, "   ") == text

    def test_no_match_returns_unchanged(self):
        escaped = _html.escape("The quick brown fox")
        quote = _html.escape("purple elephant")
        result = _inject_mark(escaped, quote)
        assert result == escaped
        assert OPEN not in result

    def test_pass3_first_sentence_on_ellipsis_quote(self):
        """Quote containing '...' triggers Pass 3: match only first sentence."""
        transcript = _html.escape(
            "The onboarding is really confusing. I hope it gets better soon."
        )
        # LLM-style quote stitching two non-adjacent turns with ellipsis
        quote = _html.escape(
            "The onboarding is really confusing... I hope it gets better"
        )
        result = _inject_mark(transcript, quote)
        assert OPEN in result  # First sentence matched

    def test_pass2_flexible_whitespace(self):
        """Pass 2 word-by-word regex allows any whitespace between words."""
        transcript = _html.escape("users\nstruggle\nwith\nonboarding")
        quote = _html.escape("users struggle with onboarding")
        result = _inject_mark(transcript, quote)
        assert OPEN in result

    def test_html_escaped_special_chars(self):
        """Works when both inputs are HTML-escaped."""
        transcript = _html.escape("Tom & Jerry: costs <100 dollars")
        quote = _html.escape("Tom & Jerry")
        result = _inject_mark(transcript, quote)
        assert OPEN in result

    def test_exact_mark_placement(self):
        escaped = "The quick brown fox"
        quote = "quick brown"
        result = _inject_mark(escaped, quote)
        assert result == f"The {OPEN}quick brown{CLOSE} fox"

    def test_mark_not_duplicated_on_exact_match(self):
        escaped = "repeat repeat repeat"
        result = _inject_mark(escaped, "repeat")
        assert result.count(OPEN) == 1

    def test_long_transcript_with_match_near_end(self):
        body = "A " * 500
        tail = "special phrase"
        transcript = body + tail
        result = _inject_mark(transcript, "special phrase")
        assert OPEN in result
        assert result.endswith(f"{OPEN}special phrase{CLOSE}")

    def test_html_entities_in_quote(self):
        """&amp; in both transcript and quote must match correctly."""
        raw_transcript = "We sell widgets & gadgets for all occasions"
        raw_quote = "widgets & gadgets"
        transcript = _html.escape(raw_transcript)
        quote = _html.escape(raw_quote)
        result = _inject_mark(transcript, quote)
        assert OPEN in result
