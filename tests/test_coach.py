"""Unit tests for the Interview Coach feature business logic.

Covers:
- Coach score trend aggregation
- Top stop-doing / keep-doing frequency analysis
- CoachDetailItem timestamp extraction logic
- Score bucket labeling (green/amber/red thresholds)
- Coach history context building for prep
- DB-backed InterviewFeedback CRUD
"""
import json
import pytest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cont_synth.state.core import (
    CoachDetailItem,
    CoachFreqItem,
    CoachScorePoint,
)


# ---------------------------------------------------------------------------
# Helpers / replicas of state logic
# ---------------------------------------------------------------------------

def _score_color(score: int) -> str:
    """Replica of the score → color mapping in coach UI."""
    if score >= 8:
        return "green"
    elif score >= 5:
        return "amber"
    return "red"


def _aggregate_frequency(lists_of_items: list[list[str]]) -> list[CoachFreqItem]:
    """
    Replica of top_stop_doing / top_keep_doing aggregation in load_coach_data().
    Counts frequency of each unique item across all lists, returns sorted descending.
    """
    counts: dict[str, int] = {}
    for items in lists_of_items:
        for item in items:
            text = item.strip()
            if text:
                counts[text] = counts.get(text, 0) + 1
    return sorted(
        [CoachFreqItem(text=t, count=c) for t, c in counts.items()],
        key=lambda x: -x.count,
    )


def _build_score_history(
    feedbacks: list[dict],
) -> list[CoachScorePoint]:
    """
    Replica of score-trend building in load_coach_data().
    feedbacks is a list of dicts with keys: interview_id, score, date_str.
    """
    return [
        CoachScorePoint(
            date=f["date_str"],
            score=f["score"],
            interview_id=f["interview_id"],
        )
        for f in feedbacks
    ]


def _extract_first_timestamp(text: str) -> str:
    """
    Replica of the first-timestamp extraction in load_coach_data().
    Returns the first '(H:MM)' or '(MM:SS)' style marker found, or ''.
    """
    import re
    match = re.search(r"\((\d+:\d+)\)", text)
    return match.group(1) if match else ""


def _extract_all_timestamps_str(text: str) -> str:
    """Replica of all-timestamps extraction."""
    import re
    matches = re.findall(r"\((\d+:\d+)\)", text)
    return ", ".join(matches)


def _strip_timestamps(text: str) -> str:
    """Replica of clean text without timestamp markers."""
    import re
    return re.sub(r"\s*\(\d+:\d+\)", "", text).strip()


@dataclass
class _MockFeedback:
    interview_id: int
    score: int
    keep_doing: str = ""
    stop_doing: str = ""
    start_doing: str = ""
    date_str: str = "2026-01-01"


# ---------------------------------------------------------------------------
# Tests: score color thresholds
# ---------------------------------------------------------------------------

class TestScoreColorThresholds:
    def test_score_1_is_red(self):
        assert _score_color(1) == "red"

    def test_score_4_is_red(self):
        assert _score_color(4) == "red"

    def test_score_5_is_amber(self):
        assert _score_color(5) == "amber"

    def test_score_7_is_amber(self):
        assert _score_color(7) == "amber"

    def test_score_8_is_green(self):
        assert _score_color(8) == "green"

    def test_score_10_is_green(self):
        assert _score_color(10) == "green"

    @pytest.mark.parametrize("score,expected", [
        (1, "red"), (2, "red"), (3, "red"), (4, "red"),
        (5, "amber"), (6, "amber"), (7, "amber"),
        (8, "green"), (9, "green"), (10, "green"),
    ])
    def test_all_score_buckets(self, score, expected):
        assert _score_color(score) == expected


# ---------------------------------------------------------------------------
# Tests: frequency aggregation for stop/keep/start doing
# ---------------------------------------------------------------------------

class TestFrequencyAggregation:
    def test_empty_returns_empty(self):
        assert _aggregate_frequency([]) == []

    def test_empty_lists_return_empty(self):
        assert _aggregate_frequency([[], [], []]) == []

    def test_single_item_once(self):
        result = _aggregate_frequency([["Ask about workarounds"]])
        assert len(result) == 1
        assert result[0].text == "Ask about workarounds"
        assert result[0].count == 1

    def test_repeated_item_has_higher_count(self):
        items = [
            ["Ask about workarounds"],
            ["Ask about workarounds"],
            ["Use silence"],
        ]
        result = _aggregate_frequency(items)
        top = result[0]
        assert top.text == "Ask about workarounds"
        assert top.count == 2

    def test_sorted_by_frequency_descending(self):
        items = [
            ["A"],
            ["B", "A"],
            ["B", "A"],
        ]
        result = _aggregate_frequency(items)
        assert result[0].text == "A"
        assert result[0].count == 3
        assert result[1].text == "B"
        assert result[1].count == 2

    def test_all_unique_items_count_one(self):
        items = [["Item 1"], ["Item 2"], ["Item 3"]]
        result = _aggregate_frequency(items)
        assert all(r.count == 1 for r in result)
        assert len(result) == 3

    def test_whitespace_stripped_before_counting(self):
        items = [["  Leading spaces  "], ["Leading spaces"]]
        result = _aggregate_frequency(items)
        # Both should count as the same item after strip
        assert result[0].count == 2

    def test_empty_strings_excluded(self):
        items = [["", "Real item", ""]]
        result = _aggregate_frequency(items)
        assert len(result) == 1
        assert result[0].text == "Real item"


# ---------------------------------------------------------------------------
# Tests: score trend history building
# ---------------------------------------------------------------------------

class TestScoreHistory:
    def test_empty_feedback_returns_empty(self):
        result = _build_score_history([])
        assert result == []

    def test_single_feedback_point(self):
        result = _build_score_history([{"interview_id": 1, "score": 8, "date_str": "2026-01-15"}])
        assert len(result) == 1
        assert result[0].score == 8
        assert result[0].interview_id == 1
        assert result[0].date == "2026-01-15"

    def test_multiple_feedback_points_in_order(self):
        feedbacks = [
            {"interview_id": 1, "score": 6, "date_str": "2026-01-01"},
            {"interview_id": 2, "score": 7, "date_str": "2026-01-15"},
            {"interview_id": 3, "score": 8, "date_str": "2026-02-01"},
        ]
        result = _build_score_history(feedbacks)
        assert len(result) == 3
        assert result[0].score == 6
        assert result[2].score == 8

    def test_all_score_values_preserved(self):
        feedbacks = [{"interview_id": i, "score": i + 1, "date_str": "2026-01-01"} for i in range(10)]
        result = _build_score_history(feedbacks)
        scores = [p.score for p in result]
        assert scores == list(range(1, 11))

    def test_date_format_preserved(self):
        result = _build_score_history([{"interview_id": 1, "score": 7, "date_str": "2026-03-07"}])
        assert result[0].date == "2026-03-07"


# ---------------------------------------------------------------------------
# Tests: timestamp extraction from coach feedback text
# ---------------------------------------------------------------------------

class TestTimestampExtraction:
    def test_no_timestamp_returns_empty(self):
        text = "Asked about workarounds for the billing flow."
        assert _extract_first_timestamp(text) == ""

    def test_extracts_single_timestamp(self):
        text = "Used good silence (2:47) when the user hesitated."
        assert _extract_first_timestamp(text) == "2:47"

    def test_extracts_first_of_multiple_timestamps(self):
        text = "Good question at (1:05) and again at (6:43)."
        assert _extract_first_timestamp(text) == "1:05"

    def test_all_timestamps_extracted(self):
        text = "Behavior observed at (0:47) then repeated at (3:22) and (7:48)."
        result = _extract_all_timestamps_str(text)
        assert "0:47" in result
        assert "3:22" in result
        assert "7:48" in result

    def test_all_timestamps_comma_separated(self):
        text = "Items (1:05) and (2:10)."
        result = _extract_all_timestamps_str(text)
        assert ", " in result

    def test_clean_text_strips_timestamps(self):
        text = "Used good silence (2:47) when the user hesitated."
        clean = _strip_timestamps(text)
        assert "(2:47)" not in clean
        assert "Used good silence" in clean

    def test_clean_text_multiple_timestamps(self):
        text = "Observed (1:05) and also (3:22)."
        clean = _strip_timestamps(text)
        assert "(1:05)" not in clean
        assert "(3:22)" not in clean

    def test_no_timestamp_text_unchanged(self):
        text = "No timestamps in this text at all."
        clean = _strip_timestamps(text)
        assert clean == text


# ---------------------------------------------------------------------------
# Tests: CoachDetailItem construction
# ---------------------------------------------------------------------------

class TestCoachDetailItemConstruction:
    def test_build_from_text_with_timestamp(self):
        raw = "Used silence effectively (2:47) during the interview."
        item = CoachDetailItem(
            text=_strip_timestamps(raw),
            first_timestamp=_extract_first_timestamp(raw),
            all_timestamps_str=_extract_all_timestamps_str(raw),
        )
        assert "2:47" not in item.text
        assert item.first_timestamp == "2:47"
        assert item.all_timestamps_str == "2:47"

    def test_build_from_text_no_timestamp(self):
        raw = "Good follow-up questions throughout."
        item = CoachDetailItem(
            text=raw,
            first_timestamp=_extract_first_timestamp(raw),
            all_timestamps_str=_extract_all_timestamps_str(raw),
        )
        assert item.text == raw
        assert item.first_timestamp == ""
        assert item.all_timestamps_str == ""

    def test_multiple_timestamps_in_one_item(self):
        raw = "Repeated pattern (1:05) and confirmed again (3:22)."
        item = CoachDetailItem(
            text=_strip_timestamps(raw),
            first_timestamp=_extract_first_timestamp(raw),
            all_timestamps_str=_extract_all_timestamps_str(raw),
        )
        assert item.first_timestamp == "1:05"
        assert "3:22" in item.all_timestamps_str


# ---------------------------------------------------------------------------
# Tests: coach history context for prep (last N feedback items)
# ---------------------------------------------------------------------------

def _get_coach_history_context(feedbacks: list[_MockFeedback], limit: int = 3) -> list[_MockFeedback]:
    """Replica of _get_coach_history_context() in InterviewPrepStateMixin."""
    return feedbacks[-limit:] if feedbacks else []


class TestCoachHistoryContext:
    def test_empty_feedback_returns_empty(self):
        assert _get_coach_history_context([]) == []

    def test_returns_up_to_three(self):
        feedbacks = [_MockFeedback(i, score=i + 1) for i in range(10)]
        result = _get_coach_history_context(feedbacks, limit=3)
        assert len(result) == 3

    def test_returns_most_recent(self):
        feedbacks = [_MockFeedback(i, score=i + 1) for i in range(5)]
        result = _get_coach_history_context(feedbacks, limit=3)
        assert result[-1].score == 5  # last one is most recent

    def test_fewer_than_limit_returns_all(self):
        feedbacks = [_MockFeedback(i, score=5) for i in range(2)]
        result = _get_coach_history_context(feedbacks, limit=3)
        assert len(result) == 2

    def test_exactly_limit_returns_all(self):
        feedbacks = [_MockFeedback(i, score=5) for i in range(3)]
        result = _get_coach_history_context(feedbacks, limit=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Tests: DB-backed InterviewFeedback with coach data
# ---------------------------------------------------------------------------

class TestInterviewFeedbackDB:
    def test_json_stop_doing_round_trip(self, db_session):
        from cont_synth.models import Interview, InterviewFeedback, Persona, Product

        product = Product(name="Coach DB WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="Coach Persona DB")
        db_session.add(persona)
        db_session.commit()
        db_session.refresh(persona)

        interview = Interview(
            product_id=product.id,
            persona_id=persona.id,
            transcript="T",
            quality_score=75,
            feedback="",
            memorable_quote="",
        )
        db_session.add(interview)
        db_session.commit()
        db_session.refresh(interview)

        stop_doing = json.dumps(["Leading questions", "Hypotheticals", "Interrupting"])
        feedback = InterviewFeedback(
            interview_id=interview.id,
            score=6,
            stop_doing=stop_doing,
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        reloaded_items = json.loads(feedback.stop_doing)
        assert "Leading questions" in reloaded_items
        assert len(reloaded_items) == 3

    def test_all_feedback_fields_persisted(self, db_session):
        from cont_synth.models import Interview, InterviewFeedback, Persona, Product

        product = Product(name="WS All Fields")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="All Fields Persona")
        db_session.add(persona)
        db_session.commit()
        db_session.refresh(persona)

        interview = Interview(
            product_id=product.id,
            persona_id=persona.id,
            transcript="T",
            quality_score=80,
            feedback="",
            memorable_quote="",
        )
        db_session.add(interview)
        db_session.commit()
        db_session.refresh(interview)

        feedback = InterviewFeedback(
            interview_id=interview.id,
            score=9,
            keep_doing=json.dumps(["Great silence", "Good follow-ups"]),
            stop_doing=json.dumps(["Leading questions"]),
            start_doing=json.dumps(["Ask about workarounds"]),
            trend_analysis="Consistently improving.",
        )
        db_session.add(feedback)
        db_session.commit()
        feedback_id = feedback.id

        reloaded = db_session.get(type(feedback), feedback_id)
        assert reloaded.score == 9
        assert reloaded.trend_analysis == "Consistently improving."
        keep = json.loads(reloaded.keep_doing)
        assert len(keep) == 2

    def test_multiple_interviews_each_have_feedback(self, db_session):
        from cont_synth.models import Interview, InterviewFeedback, Persona, Product
        from sqlmodel import select

        product = Product(name="Multi-Interview WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        for i in range(3):
            persona = Persona(name=f"Persona Multi {i}")
            db_session.add(persona)
            db_session.commit()
            db_session.refresh(persona)

            interview = Interview(
                product_id=product.id,
                persona_id=persona.id,
                transcript="T",
                quality_score=70 + i,
                feedback="",
                memorable_quote="",
            )
            db_session.add(interview)
            db_session.commit()
            db_session.refresh(interview)

            feedback = InterviewFeedback(interview_id=interview.id, score=5 + i)
            db_session.add(feedback)
        db_session.commit()

        all_feedback = db_session.exec(select(InterviewFeedback)).all()
        assert len(all_feedback) == 3
        scores = {f.score for f in all_feedback}
        assert scores == {5, 6, 7}
