"""Unit tests for Pydantic LLM response schemas."""
import pytest
from pydantic import ValidationError

from schema import (
    CoachFeedback,
    OpportunityExtraction,
    QualityCheck,
    InterviewMetadata,
    InterviewSnapshot,
    OpportunityMatch,
    DedupeResult,
)


class TestOpportunityExtraction:
    def test_valid_creation(self):
        opp = OpportunityExtraction(
            theme="Onboarding",
            opportunity_statement="Users struggle to set up their first project.",
            source_quote="I spent three hours just trying to configure the settings.",
        )
        assert opp.theme == "Onboarding"
        assert "struggle" in opp.opportunity_statement
        assert "three hours" in opp.source_quote

    def test_missing_theme_raises(self):
        with pytest.raises(ValidationError):
            OpportunityExtraction(
                opportunity_statement="Some statement",
                source_quote="Some quote",
            )

    def test_missing_statement_raises(self):
        with pytest.raises(ValidationError):
            OpportunityExtraction(
                theme="Theme",
                source_quote="Some quote",
            )

    def test_missing_quote_raises(self):
        with pytest.raises(ValidationError):
            OpportunityExtraction(
                theme="Theme",
                opportunity_statement="Some statement",
            )

    def test_empty_strings_allowed(self):
        """Empty strings pass Pydantic validation (not business-logic validated here)."""
        opp = OpportunityExtraction(theme="", opportunity_statement="", source_quote="")
        assert opp.theme == ""


class TestQualityCheck:
    def test_valid_creation(self):
        qc = QualityCheck(score=85, feedback="Good interview with actionable insights.")
        assert qc.score == 85
        assert qc.feedback

    def test_score_zero(self):
        qc = QualityCheck(score=0, feedback="No useful data")
        assert qc.score == 0

    def test_score_100(self):
        qc = QualityCheck(score=100, feedback="Perfect interview")
        assert qc.score == 100

    def test_negative_score_allowed(self):
        """Schema accepts any int; business rules are not enforced here."""
        qc = QualityCheck(score=-1, feedback="Edge case")
        assert qc.score == -1

    def test_missing_score_raises(self):
        with pytest.raises(ValidationError):
            QualityCheck(feedback="Some feedback")

    def test_missing_feedback_raises(self):
        with pytest.raises(ValidationError):
            QualityCheck(score=50)


class TestInterviewMetadata:
    def test_all_fields(self):
        meta = InterviewMetadata(
            duration_minutes=45,
            interview_date="2025-01-15",
            participant_names=["Alice", "Bob"],
            participant_roles=["interviewee", "interviewer"],
        )
        assert meta.duration_minutes == 45
        assert meta.interview_date == "2025-01-15"
        assert meta.participant_names == ["Alice", "Bob"]
        assert meta.participant_roles == ["interviewer", "interviewee"] or \
               meta.participant_roles == ["interviewee", "interviewer"]

    def test_all_none(self):
        meta = InterviewMetadata(
            duration_minutes=None,
            interview_date=None,
            participant_names=None,
            participant_roles=None,
        )
        assert meta.duration_minutes is None
        assert meta.interview_date is None
        assert meta.participant_names is None
        assert meta.participant_roles is None

    def test_empty_participants_list(self):
        meta = InterviewMetadata(
            duration_minutes=30,
            interview_date="2025-01-01",
            participant_names=[],
            participant_roles=[],
        )
        assert meta.participant_names == []
        assert meta.participant_roles == []

    def test_many_participants(self):
        names = ["Alice", "Bob", "Charlie", "Dave", "Eve"]
        roles = ["interviewee"] * 5
        meta = InterviewMetadata(
            duration_minutes=60,
            interview_date="2025-06-01",
            participant_names=names,
            participant_roles=roles,
        )
        assert len(meta.participant_names) == 5
        assert len(meta.participant_roles) == 5

    def test_iso_date_format_stored_as_string(self):
        meta = InterviewMetadata(
            duration_minutes=None,
            interview_date="2025-12-31",
            participant_names=None,
            participant_roles=None,
        )
        assert meta.interview_date == "2025-12-31"

    def test_parallel_names_and_roles(self):
        """participant_names and participant_roles are parallel lists."""
        meta = InterviewMetadata(
            duration_minutes=45,
            interview_date="2025-03-01",
            participant_names=["Alice", "Bob"],
            participant_roles=["interviewee", "interviewer"],
        )
        assert len(meta.participant_names) == len(meta.participant_roles)
        assert meta.participant_roles[1] == "interviewer"

    def test_missing_required_fields_raise(self):
        with pytest.raises(ValidationError):
            InterviewMetadata(duration_minutes=30, interview_date="2025-01-01")


class TestInterviewSnapshot:
    def test_valid_with_opportunities(self):
        snapshot = InterviewSnapshot(
            quality_check=QualityCheck(score=70, feedback="OK interview"),
            opportunities=[
                OpportunityExtraction(
                    theme="Billing",
                    opportunity_statement="Users can't find invoice history.",
                    source_quote="Where are my old invoices?",
                )
            ],
            memorable_quote="This product is saving us hours every week!",
            metadata=None,
        )
        assert len(snapshot.opportunities) == 1
        assert snapshot.quality_check.score == 70

    def test_empty_opportunities(self):
        snapshot = InterviewSnapshot(
            quality_check=QualityCheck(score=30, feedback="No insights"),
            opportunities=[],
            memorable_quote="Not much to say",
            metadata=None,
        )
        assert snapshot.opportunities == []

    def test_with_full_metadata(self):
        snapshot = InterviewSnapshot(
            quality_check=QualityCheck(score=80, feedback="Good"),
            opportunities=[],
            memorable_quote="Quote here",
            metadata=InterviewMetadata(
                duration_minutes=60,
                interview_date="2025-03-01",
                participant_names=["Charlie"],
                participant_roles=["interviewee"],
            ),
        )
        assert snapshot.metadata is not None
        assert snapshot.metadata.duration_minutes == 60

    def test_multiple_opportunities(self):
        opps = [
            OpportunityExtraction(theme=f"Theme{i}", opportunity_statement=f"Need {i}", source_quote=f"Q{i}")
            for i in range(5)
        ]
        snapshot = InterviewSnapshot(
            quality_check=QualityCheck(score=90, feedback="Excellent"),
            opportunities=opps,
            memorable_quote="Very insightful",
            metadata=None,
        )
        assert len(snapshot.opportunities) == 5

    def test_missing_quality_check_raises(self):
        with pytest.raises(ValidationError):
            InterviewSnapshot(
                opportunities=[],
                memorable_quote="Quote",
                metadata=None,
            )


class TestOpportunityMatch:
    def test_new_opportunity_no_match(self):
        match = OpportunityMatch(
            new_opportunity_statement="New need discovered",
            matched_existing_id=None,
        )
        assert match.matched_existing_id is None
        assert match.new_opportunity_statement == "New need discovered"

    def test_matched_existing_opportunity(self):
        match = OpportunityMatch(
            new_opportunity_statement="Existing need rephrased",
            matched_existing_id=42,
        )
        assert match.matched_existing_id == 42

    def test_matched_existing_id_one(self):
        match = OpportunityMatch(
            new_opportunity_statement="Matches first opp",
            matched_existing_id=1,
        )
        assert match.matched_existing_id == 1

    def test_missing_statement_raises(self):
        with pytest.raises(ValidationError):
            OpportunityMatch(matched_existing_id=1)


class TestDedupeResult:
    def test_empty_matches(self):
        result = DedupeResult(matches=[])
        assert result.matches == []

    def test_single_match(self):
        result = DedupeResult(
            matches=[
                OpportunityMatch(new_opportunity_statement="Need A", matched_existing_id=1)
            ]
        )
        assert len(result.matches) == 1

    def test_multiple_matches_mixed(self):
        result = DedupeResult(
            matches=[
                OpportunityMatch(new_opportunity_statement="Need A", matched_existing_id=1),
                OpportunityMatch(new_opportunity_statement="Need B", matched_existing_id=None),
                OpportunityMatch(new_opportunity_statement="Need C", matched_existing_id=7),
            ]
        )
        assert len(result.matches) == 3
        assert result.matches[0].matched_existing_id == 1
        assert result.matches[1].matched_existing_id is None
        assert result.matches[2].matched_existing_id == 7

    def test_missing_matches_field_raises(self):
        with pytest.raises(ValidationError):
            DedupeResult()


class TestCoachFeedback:
    def test_valid_creation(self):
        feedback = CoachFeedback(
            score=8,
            keep_doing=["Used silence effectively", "Good follow-up questions"],
            stop_doing=["Asked leading questions"],
            start_doing=["Ask about workarounds"],
            trend_analysis="Improving steadily over time.",
        )
        assert feedback.score == 8
        assert len(feedback.keep_doing) == 2
        assert len(feedback.stop_doing) == 1
        assert len(feedback.start_doing) == 1
        assert "Improving" in feedback.trend_analysis

    def test_score_range_valid(self):
        for score in [1, 5, 10]:
            fb = CoachFeedback(
                score=score,
                keep_doing=[],
                stop_doing=[],
                start_doing=[],
                trend_analysis="",
            )
            assert fb.score == score

    def test_empty_lists_allowed(self):
        fb = CoachFeedback(
            score=5,
            keep_doing=[],
            stop_doing=[],
            start_doing=[],
            trend_analysis="No trend data.",
        )
        assert fb.keep_doing == []
        assert fb.stop_doing == []
        assert fb.start_doing == []

    def test_missing_score_raises(self):
        with pytest.raises(ValidationError):
            CoachFeedback(
                keep_doing=[],
                stop_doing=[],
                start_doing=[],
                trend_analysis="",
            )

    def test_missing_keep_doing_raises(self):
        with pytest.raises(ValidationError):
            CoachFeedback(
                score=7,
                stop_doing=[],
                start_doing=[],
                trend_analysis="",
            )

    def test_many_items_in_lists(self):
        items = [f"Action {i}" for i in range(10)]
        fb = CoachFeedback(
            score=9,
            keep_doing=items,
            stop_doing=items[:3],
            start_doing=items[:2],
            trend_analysis="Trending up",
        )
        assert len(fb.keep_doing) == 10

    def test_trend_analysis_stored_as_string(self):
        fb = CoachFeedback(
            score=6,
            keep_doing=[],
            stop_doing=[],
            start_doing=[],
            trend_analysis="Score has been consistently above 7 in recent sessions.",
        )
        assert isinstance(fb.trend_analysis, str)

    def test_all_three_sections_are_lists(self):
        fb = CoachFeedback(
            score=7,
            keep_doing=["A"],
            stop_doing=["B"],
            start_doing=["C"],
            trend_analysis="Stable.",
        )
        assert isinstance(fb.keep_doing, list)
        assert isinstance(fb.stop_doing, list)
        assert isinstance(fb.start_doing, list)
