"""Unit tests for synthesis workflow business logic.

Covers the pure-Python logic extracted from InterviewSynthesisStateMixin:
- Pending opportunity state management (select/deselect, match to existing)
- Theme and statement resolution when confirming synthesis
- Participant role assignment
- LLM usage tracking data structures
- Synthesis guard clauses
- Coach feedback integration
"""
import json
import pytest
from sqlmodel import select

from cont_synth.state.core import PendingOppItem, PendingParticipantItem, PendingLlmUsage


# ---------------------------------------------------------------------------
# Helpers: replicas of state logic
# ---------------------------------------------------------------------------

def _toggle_opp_selected(opps: list[PendingOppItem], index: int) -> list[PendingOppItem]:
    """Replica of update_pending_opp_selected logic."""
    return [
        PendingOppItem(
            index=o.index,
            opportunity_statement=o.opportunity_statement,
            theme=o.theme,
            source_quote=o.source_quote,
            matched_existing_id=o.matched_existing_id,
            matched_existing_statement=o.matched_existing_statement,
            selected=not o.selected if o.index == index else o.selected,
        )
        for o in opps
    ]


def _set_opp_match(opps: list[PendingOppItem], index: int, matched_id: int, matched_statement: str) -> list[PendingOppItem]:
    """Replica of update_pending_opp_matched logic."""
    return [
        PendingOppItem(
            index=o.index,
            opportunity_statement=o.opportunity_statement,
            theme=o.theme,
            source_quote=o.source_quote,
            matched_existing_id=matched_id if o.index == index else o.matched_existing_id,
            matched_existing_statement=matched_statement if o.index == index else o.matched_existing_statement,
            selected=o.selected,
        )
        for o in opps
    ]


def _count_selected(opps: list[PendingOppItem]) -> int:
    """Replica of selected_opp_count @rx.var."""
    return sum(1 for o in opps if o.selected)


def _is_new_opp(matched_existing_id: int) -> bool:
    """An opp is new when matched_existing_id == -1."""
    return matched_existing_id == -1


def _resolve_final_statement(opp: PendingOppItem) -> str:
    """
    Replica of the statement resolution in confirm_synthesis:
    if matched, keep the existing statement; otherwise use new.
    """
    if opp.matched_existing_id != -1 and opp.matched_existing_statement:
        return opp.matched_existing_statement
    return opp.opportunity_statement


def _build_participants_from_roles(
    names: list[str], roles: list[str]
) -> list[dict]:
    """Replica of participant assembly in confirm_synthesis."""
    return [
        {"name": name, "is_team_member": role == "interviewer"}
        for name, role in zip(names, roles)
    ]


def _validate_coach_score(score: int) -> bool:
    """Score must be 1–10 to be valid."""
    return 1 <= score <= 10


def _build_pending_llm_usage(
    model_name: str,
    operation: str,
    prompt_tokens: int,
    output_tokens: int,
) -> PendingLlmUsage:
    return PendingLlmUsage(
        model_name=model_name,
        operation=operation,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
        total_tokens=prompt_tokens + output_tokens,
    )


# ---------------------------------------------------------------------------
# Tests: toggle pending opp selection
# ---------------------------------------------------------------------------

def _make_pending_opp(index: int, statement: str = "Need X", selected: bool = True) -> PendingOppItem:
    return PendingOppItem(
        index=index,
        opportunity_statement=statement,
        theme="General",
        source_quote="Some quote",
        selected=selected,
    )


class TestTogglePendingOppSelected:
    def test_selected_becomes_unselected(self):
        opps = [_make_pending_opp(0, selected=True)]
        result = _toggle_opp_selected(opps, 0)
        assert result[0].selected is False

    def test_unselected_becomes_selected(self):
        opps = [_make_pending_opp(0, selected=False)]
        result = _toggle_opp_selected(opps, 0)
        assert result[0].selected is True

    def test_only_target_changes(self):
        opps = [_make_pending_opp(0, selected=True), _make_pending_opp(1, selected=True)]
        result = _toggle_opp_selected(opps, 0)
        assert result[0].selected is False
        assert result[1].selected is True

    def test_all_fields_preserved(self):
        opps = [_make_pending_opp(0, statement="Invoice search is slow", selected=True)]
        result = _toggle_opp_selected(opps, 0)
        assert result[0].opportunity_statement == "Invoice search is slow"
        assert result[0].theme == "General"
        assert result[0].source_quote == "Some quote"
        assert result[0].index == 0

    def test_empty_list(self):
        assert _toggle_opp_selected([], 0) == []

    def test_count_updated_correctly(self):
        opps = [_make_pending_opp(i, selected=True) for i in range(5)]
        result = _toggle_opp_selected(opps, 2)
        assert _count_selected(result) == 4

    def test_double_toggle_restores_original(self):
        opps = [_make_pending_opp(0, selected=True)]
        result = _toggle_opp_selected(opps, 0)
        result = _toggle_opp_selected(result, 0)
        assert result[0].selected is True


class TestSelectedOppCount:
    def test_all_selected(self):
        opps = [_make_pending_opp(i, selected=True) for i in range(5)]
        assert _count_selected(opps) == 5

    def test_none_selected(self):
        opps = [_make_pending_opp(i, selected=False) for i in range(3)]
        assert _count_selected(opps) == 0

    def test_partial_selection(self):
        opps = [
            _make_pending_opp(0, selected=True),
            _make_pending_opp(1, selected=False),
            _make_pending_opp(2, selected=True),
        ]
        assert _count_selected(opps) == 2

    def test_empty_list(self):
        assert _count_selected([]) == 0


# ---------------------------------------------------------------------------
# Tests: setting match to existing opportunity
# ---------------------------------------------------------------------------

class TestSetOppMatch:
    def test_set_match_on_target_opp(self):
        opps = [_make_pending_opp(0), _make_pending_opp(1)]
        result = _set_opp_match(opps, 0, matched_id=42, matched_statement="Existing statement")
        assert result[0].matched_existing_id == 42
        assert result[0].matched_existing_statement == "Existing statement"

    def test_other_opps_unchanged(self):
        opps = [_make_pending_opp(0), _make_pending_opp(1)]
        result = _set_opp_match(opps, 0, matched_id=42, matched_statement="Existing")
        assert result[1].matched_existing_id == -1
        assert result[1].matched_existing_statement == ""

    def test_clear_match_with_minus_one(self):
        opps = [_make_pending_opp(0)]
        # First set a match
        result = _set_opp_match(opps, 0, matched_id=42, matched_statement="Old")
        # Then clear it
        result = _set_opp_match(result, 0, matched_id=-1, matched_statement="")
        assert result[0].matched_existing_id == -1

    def test_is_new_opp_default(self):
        opp = _make_pending_opp(0)
        assert _is_new_opp(opp.matched_existing_id) is True

    def test_is_new_opp_after_match(self):
        opps = [_make_pending_opp(0)]
        result = _set_opp_match(opps, 0, matched_id=5, matched_statement="Existing")
        assert _is_new_opp(result[0].matched_existing_id) is False


# ---------------------------------------------------------------------------
# Tests: statement resolution at confirm_synthesis
# ---------------------------------------------------------------------------

class TestStatementResolution:
    def test_new_opp_uses_synthesized_statement(self):
        opp = PendingOppItem(
            index=0,
            opportunity_statement="New need discovered",
            theme="General",
            source_quote="Q",
            matched_existing_id=-1,
        )
        assert _resolve_final_statement(opp) == "New need discovered"

    def test_matched_opp_uses_existing_statement(self):
        opp = PendingOppItem(
            index=0,
            opportunity_statement="Rephrased version",
            theme="General",
            source_quote="Q",
            matched_existing_id=5,
            matched_existing_statement="Original statement from DB",
        )
        assert _resolve_final_statement(opp) == "Original statement from DB"

    def test_matched_but_empty_existing_statement_uses_synthesized(self):
        opp = PendingOppItem(
            index=0,
            opportunity_statement="Synthesized version",
            theme="General",
            source_quote="Q",
            matched_existing_id=5,
            matched_existing_statement="",
        )
        # Empty existing statement → fall back to synthesized
        assert _resolve_final_statement(opp) == "Synthesized version"


# ---------------------------------------------------------------------------
# Tests: participant role assembly
# ---------------------------------------------------------------------------

class TestParticipantRoleAssembly:
    def test_interviewee_not_team_member(self):
        result = _build_participants_from_roles(["Alice"], ["interviewee"])
        assert result[0]["is_team_member"] is False

    def test_interviewer_is_team_member(self):
        result = _build_participants_from_roles(["Bob"], ["interviewer"])
        assert result[0]["is_team_member"] is True

    def test_mixed_roles(self):
        result = _build_participants_from_roles(
            ["Alice", "Bob", "Charlie"],
            ["interviewee", "interviewer", "interviewee"]
        )
        assert result[0]["is_team_member"] is False
        assert result[1]["is_team_member"] is True
        assert result[2]["is_team_member"] is False

    def test_names_preserved(self):
        result = _build_participants_from_roles(["Alice", "Bob"], ["interviewee", "interviewer"])
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    def test_empty_lists(self):
        assert _build_participants_from_roles([], []) == []

    def test_length_matches_input(self):
        names = ["A", "B", "C", "D"]
        roles = ["interviewee"] * 4
        result = _build_participants_from_roles(names, roles)
        assert len(result) == 4


# ---------------------------------------------------------------------------
# Tests: PendingParticipantItem role editing
# ---------------------------------------------------------------------------

class TestPendingParticipantRoles:
    def test_default_role_is_interviewee(self):
        item = PendingParticipantItem(index=0, name="Alice")
        assert item.role == "interviewee"

    def test_set_role_to_interviewer(self):
        item = PendingParticipantItem(index=1, name="Bob", role="interviewer")
        assert item.role == "interviewer"

    def test_index_is_tracked(self):
        items = [PendingParticipantItem(index=i, name=f"Person {i}") for i in range(5)]
        for i, item in enumerate(items):
            assert item.index == i

    def test_both_roles_are_valid(self):
        for role in ["interviewee", "interviewer"]:
            item = PendingParticipantItem(index=0, name="X", role=role)
            assert item.role == role


# ---------------------------------------------------------------------------
# Tests: coach score validation
# ---------------------------------------------------------------------------

class TestCoachScoreValidation:
    def test_valid_scores(self):
        for score in range(1, 11):
            assert _validate_coach_score(score) is True

    def test_score_zero_invalid(self):
        assert _validate_coach_score(0) is False

    def test_score_eleven_invalid(self):
        assert _validate_coach_score(11) is False

    def test_boundary_one(self):
        assert _validate_coach_score(1) is True

    def test_boundary_ten(self):
        assert _validate_coach_score(10) is True


# ---------------------------------------------------------------------------
# Tests: LLM usage token tracking
# ---------------------------------------------------------------------------

class TestLlmUsageTracking:
    def test_total_tokens_is_sum(self):
        usage = _build_pending_llm_usage("gemini-2.5-pro", "synthesis", 1500, 300)
        assert usage.total_tokens == 1800

    def test_model_name_preserved(self):
        usage = _build_pending_llm_usage("gemini-2.5-flash", "dedupe", 200, 100)
        assert usage.model_name == "gemini-2.5-flash"

    def test_operation_preserved(self):
        for op in ["synthesis", "dedupe", "prep", "coach"]:
            usage = _build_pending_llm_usage("model", op, 100, 50)
            assert usage.operation == op

    def test_zero_tokens(self):
        usage = _build_pending_llm_usage("model", "prep", 0, 0)
        assert usage.total_tokens == 0
        assert usage.prompt_tokens == 0
        assert usage.output_tokens == 0

    def test_large_token_counts(self):
        usage = _build_pending_llm_usage("gemini-2.5-pro", "synthesis", 50000, 10000)
        assert usage.total_tokens == 60000


# ---------------------------------------------------------------------------
# Tests: synthesis guard clause (no transcript → don't run)
# ---------------------------------------------------------------------------

def _should_run_synthesis(transcript: str, is_processing: bool) -> bool:
    """Replica of the guard in run_synthesis()."""
    return bool(transcript.strip()) and not is_processing


class TestSynthesisGuardClause:
    def test_empty_transcript_blocked(self):
        assert _should_run_synthesis("", is_processing=False) is False

    def test_whitespace_only_transcript_blocked(self):
        assert _should_run_synthesis("   \n\t  ", is_processing=False) is False

    def test_already_processing_blocked(self):
        assert _should_run_synthesis("Real transcript here.", is_processing=True) is False

    def test_valid_transcript_not_processing_allowed(self):
        assert _should_run_synthesis("Interviewee: ...", is_processing=False) is True

    def test_both_conditions_must_pass(self):
        assert _should_run_synthesis("", is_processing=True) is False
        assert _should_run_synthesis("transcript", is_processing=True) is False


# ---------------------------------------------------------------------------
# Tests: DB-backed synthesis workflow (uses db_session fixture)
# ---------------------------------------------------------------------------

class TestSynthesisDBWorkflow:
    """Tests for the DB operations that happen in confirm_synthesis()."""

    def test_interview_created_with_all_fields(self, db_session):
        from cont_synth.models import Interview, Persona, Product

        product = Product(name="Test Workspace")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="VP of Engineering")
        db_session.add(persona)
        db_session.commit()
        db_session.refresh(persona)

        interview = Interview(
            product_id=product.id,
            persona_id=persona.id,
            transcript="Full transcript text here...",
            quality_score=78,
            feedback="Good insight on billing.",
            memorable_quote="We lose 2 hours a week on this.",
            duration_minutes=45,
            interview_date="2026-02-15",
            participants='["Alice", "Bob"]',
        )
        db_session.add(interview)
        db_session.commit()
        db_session.refresh(interview)

        assert interview.id is not None
        assert interview.quality_score == 78
        assert interview.duration_minutes == 45
        assert interview.interview_date == "2026-02-15"

    def test_opportunity_created_and_linked(self, db_session):
        from cont_synth.models import Interview, InterviewOpportunityLink, Opportunity, Persona, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="SMB Owner")
        db_session.add(persona)
        db_session.commit()
        db_session.refresh(persona)

        interview = Interview(
            product_id=product.id,
            persona_id=persona.id,
            transcript="T",
            quality_score=70,
            feedback="",
            memorable_quote="",
        )
        db_session.add(interview)
        db_session.commit()
        db_session.refresh(interview)

        opp = Opportunity(product_id=product.id, statement="Need fast search", theme="Performance")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        link = InterviewOpportunityLink(
            interview_id=interview.id,
            opportunity_id=opp.id,
            source_quote="Search results take forever.",
        )
        db_session.add(link)
        db_session.commit()

        links = db_session.exec(
            select(InterviewOpportunityLink).where(
                InterviewOpportunityLink.interview_id == interview.id
            )
        ).all()
        assert len(links) == 1
        assert links[0].source_quote == "Search results take forever."

    def test_interview_feedback_linked_to_interview(self, db_session):
        from cont_synth.models import Interview, InterviewFeedback, Persona, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="Coach Test")
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
            score=8,
            keep_doing=json.dumps(["Good silence"]),
            stop_doing=json.dumps(["Leading questions"]),
            start_doing=json.dumps(["Ask about workarounds"]),
            trend_analysis="Improving.",
        )
        db_session.add(feedback)
        db_session.commit()
        db_session.refresh(feedback)

        assert feedback.interview_id == interview.id
        items = json.loads(feedback.keep_doing)
        assert "Good silence" in items

    def test_multiple_opportunities_from_one_interview(self, db_session):
        from cont_synth.models import Interview, InterviewOpportunityLink, Opportunity, Persona, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="User")
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

        for i in range(3):
            opp = Opportunity(product_id=product.id, statement=f"Need {i}", theme=f"Theme {i}")
            db_session.add(opp)
            db_session.commit()
            db_session.refresh(opp)
            link = InterviewOpportunityLink(
                interview_id=interview.id,
                opportunity_id=opp.id,
                source_quote=f"Quote for need {i}",
            )
            db_session.add(link)
        db_session.commit()

        links = db_session.exec(
            select(InterviewOpportunityLink).where(
                InterviewOpportunityLink.interview_id == interview.id
            )
        ).all()
        assert len(links) == 3

    def test_existing_opportunity_reused_not_duplicated(self, db_session):
        """When a new synthesis matches an existing opp, no duplicate is created."""
        from cont_synth.models import Interview, InterviewOpportunityLink, Opportunity, Persona, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        persona = Persona(name="User")
        db_session.add(persona)
        db_session.commit()
        db_session.refresh(persona)

        # Pre-existing opportunity
        existing_opp = Opportunity(product_id=product.id, statement="Original statement", theme="Billing")
        db_session.add(existing_opp)
        db_session.commit()
        db_session.refresh(existing_opp)

        # New interview
        interview = Interview(
            product_id=product.id, persona_id=persona.id,
            transcript="T", quality_score=70, feedback="", memorable_quote="",
        )
        db_session.add(interview)
        db_session.commit()
        db_session.refresh(interview)

        # Link to existing opp (not a new one)
        link = InterviewOpportunityLink(
            interview_id=interview.id,
            opportunity_id=existing_opp.id,
            source_quote="Another quote backing the same need.",
        )
        db_session.add(link)
        db_session.commit()

        # Only 1 opportunity should exist
        opps = db_session.exec(
            select(Opportunity).where(Opportunity.product_id == product.id)
        ).all()
        assert len(opps) == 1
        assert opps[0].statement == "Original statement"
