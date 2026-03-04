"""Unit tests for rx.Base data classes used for UI state.

These classes carry data between the backend state and the frontend.
Tests ensure correct instantiation, field types, and defaults.
"""

import pytest

# conftest.py has mocked google.generativeai before this import.
from cont_synth.state.core import (
    DashboardBarItem,
    DetailParticipantItem,
    ExperimentItem,
    InterviewHistoryItem,
    LedgerItem,
    LlmUsageItem,
    OppDetailSolution,
    OutcomeItem,
    ParticipantItem,
    PendingLlmUsage,
    PendingOppItem,
    PendingParticipantItem,
    PersonaBadge,
    PrepExperimentItem,
    PrepOppItem,
    ProductItem,
    QuoteItem,
    RecentInterviewItem,
    SolutionItem,
)


class TestProductItem:
    def test_create(self):
        item = ProductItem(id=1, name="My Workspace")
        assert item.id == 1
        assert item.name == "My Workspace"

    def test_id_is_int(self):
        item = ProductItem(id=42, name="WS")
        assert isinstance(item.id, int)

    def test_name_is_str(self):
        item = ProductItem(id=1, name="Test")
        assert isinstance(item.name, str)


class TestPersonaBadge:
    def test_create(self):
        badge = PersonaBadge(name="Power User", color="blue")
        assert badge.name == "Power User"
        assert badge.color == "blue"

    def test_all_valid_colors(self):
        colors = [
            "blue",
            "purple",
            "orange",
            "green",
            "pink",
            "teal",
            "ruby",
            "iris",
            "indigo",
        ]
        for color in colors:
            badge = PersonaBadge(name="User", color=color)
            assert badge.color == color


class TestQuoteItem:
    def test_create_with_defaults(self):
        quote = QuoteItem(
            interview_id=5,
            persona_name="Alice",
            persona_color="purple",
            text="This feature is confusing.",
        )
        assert quote.interview_id == 5
        assert quote.persona_name == "Alice"
        assert quote.opportunity_statement == ""  # default

    def test_create_with_opportunity_statement(self):
        quote = QuoteItem(
            interview_id=3,
            persona_name="Bob",
            persona_color="orange",
            text="Quote text",
            opportunity_statement="Users need better search.",
        )
        assert quote.opportunity_statement == "Users need better search."

    def test_text_preserves_newlines(self):
        text = "Line one\nLine two\nLine three"
        quote = QuoteItem(
            interview_id=1, persona_name="U", persona_color="blue", text=text
        )
        assert quote.text == text


class TestSolutionItem:
    def test_create_with_defaults(self):
        sol = SolutionItem(
            id=10,
            name="Better Search",
            description="Implement elastic search",
            status="Ideation",
        )
        assert sol.id == 10
        assert sol.parent_id is None
        assert sol.indent_level == 0

    def test_create_with_parent_and_indent(self):
        sol = SolutionItem(
            id=11,
            parent_id=10,
            name="Sub-solution",
            description="A sub-approach",
            status="Testing",
            indent_level=1,
        )
        assert sol.parent_id == 10
        assert sol.indent_level == 1

    def test_all_statuses(self):
        for status in ["Ideation", "Testing", "Discarded", "Shipped"]:
            sol = SolutionItem(id=1, name="S", description="", status=status)
            assert sol.status == status


class TestExperimentItem:
    def test_create(self):
        exp = ExperimentItem(
            id=1,
            solution_id=5,
            solution_name="Solution A",
            name="Fake Door Test",
            assumption="Users will click it",
            description="",
            success_metric="",
            method="Fake Door",
            status="Running",
            signal="Pending",
            evidence_notes="",
        )
        assert exp.id == 1
        assert exp.solution_id == 5
        assert exp.method == "Fake Door"
        assert exp.signal == "Pending"

    def test_all_methods(self):
        for method in ["Fake Door", "A/B Test", "Prototype Interview"]:
            exp = ExperimentItem(
                id=1,
                solution_id=1,
                solution_name="S",
                name="N",
                assumption="A",
                description="",
                success_metric="",
                method=method,
                status="Draft",
                signal="Pending",
                evidence_notes="",
            )
            assert exp.method == method

    def test_all_statuses(self):
        for status in ["Draft", "Running", "Concluded"]:
            exp = ExperimentItem(
                id=1,
                solution_id=1,
                solution_name="S",
                name="N",
                assumption="A",
                description="",
                success_metric="",
                method="Fake Door",
                status=status,
                signal="Pending",
                evidence_notes="",
            )
            assert exp.status == status

    def test_all_signals(self):
        for signal in ["Pending", "Validated", "Invalidated"]:
            exp = ExperimentItem(
                id=1,
                solution_id=1,
                solution_name="S",
                name="N",
                assumption="A",
                description="",
                success_metric="",
                method="A/B Test",
                status="Concluded",
                signal=signal,
                evidence_notes="",
            )
            assert exp.signal == signal

    def test_new_fields_exist_and_default_to_empty_string(self):
        exp = ExperimentItem(
            id=1,
            solution_id=1,
            solution_name="S",
            name="N",
            assumption="A",
            description="",
            success_metric="",
            method="Fake Door",
            status="Draft",
            signal="Pending",
            evidence_notes="",
        )
        assert exp.description == ""
        assert exp.success_metric == ""
        assert isinstance(exp.description, str)
        assert isinstance(exp.success_metric, str)


class TestOppDetailSolution:
    def test_create_with_defaults(self):
        sol = OppDetailSolution(
            id=5,
            name="Redesign flow",
            description="Full UX overhaul",
            status="Ideation",
        )
        assert sol.experiments == []
        assert sol.parent_id is None
        assert sol.indent_level == 0

    def test_create_with_experiments(self):
        exp = ExperimentItem(
            id=1,
            solution_id=5,
            solution_name="Redesign flow",
            name="Fake Door",
            assumption="Users want it",
            description="",
            success_metric="",
            method="Fake Door",
            status="Draft",
            signal="Pending",
            evidence_notes="",
        )
        sol = OppDetailSolution(
            id=5,
            name="Redesign flow",
            description="",
            status="Testing",
            experiments=[exp],
        )
        assert len(sol.experiments) == 1
        assert sol.experiments[0].name == "Fake Door"


class TestPendingOppItem:
    def test_defaults(self):
        item = PendingOppItem(
            index=0,
            opportunity_statement="Users need X",
            theme="Onboarding",
            source_quote="Quote text here",
        )
        assert item.selected is True
        assert item.matched_existing_id == -1
        assert item.matched_existing_statement == ""

    def test_matched_existing(self):
        item = PendingOppItem(
            index=1,
            opportunity_statement="Existing need rephrased",
            theme="Billing",
            source_quote="Quote",
            matched_existing_id=42,
            matched_existing_statement="Previous statement",
            selected=False,
        )
        assert item.matched_existing_id == 42
        assert item.matched_existing_statement == "Previous statement"
        assert item.selected is False

    def test_index_tracks_position(self):
        items = [
            PendingOppItem(
                index=i, opportunity_statement=f"Need {i}", theme="T", source_quote="Q"
            )
            for i in range(5)
        ]
        for i, item in enumerate(items):
            assert item.index == i


class TestOutcomeItem:
    def test_create(self):
        item = OutcomeItem(id=7, name="Reduce Churn")
        assert item.id == 7
        assert item.name == "Reduce Churn"


class TestLedgerItem:
    def test_create_minimal(self):
        item = LedgerItem(
            opportunity_id=1,
            theme="Performance",
            personas_affected=[],
            opportunity="Users experience slow load times.",
            status="FRESH",
            status_color="green",
            days_old=5,
            is_cross_functional=False,
            evidence=[],
        )
        assert item.opportunity_id == 1
        assert item.solutions == []
        assert item.linked_outcomes == []
        assert item.experiments == []
        assert item.parent_id == -1
        assert item.indent_level == 0

    def test_default_parent_id_is_minus_one(self):
        item = LedgerItem(
            opportunity_id=2,
            theme="T",
            personas_affected=[],
            opportunity="O",
            status="FRESH",
            status_color="green",
            days_old=0,
            is_cross_functional=False,
            evidence=[],
        )
        assert item.parent_id == -1

    def test_create_with_full_data(self):
        badge = PersonaBadge(name="Admin", color="blue")
        quote = QuoteItem(
            interview_id=1, persona_name="Admin", persona_color="blue", text="Q"
        )
        sol = SolutionItem(id=1, name="Sol", description="D", status="Ideation")
        outcome = OutcomeItem(id=1, name="Revenue Growth")

        item = LedgerItem(
            opportunity_id=3,
            parent_id=0,
            indent_level=1,
            theme="Billing",
            personas_affected=[badge],
            opportunity="Invoice search is slow",
            status="DECAYING (>21 Days)",
            status_color="yellow",
            days_old=30,
            is_cross_functional=True,
            evidence=[quote],
            solutions=[sol],
            linked_outcomes=[outcome],
        )
        assert len(item.personas_affected) == 1
        assert len(item.evidence) == 1
        assert len(item.solutions) == 1
        assert len(item.linked_outcomes) == 1
        assert item.is_cross_functional is True
        assert item.indent_level == 1

    def test_all_status_values(self):
        for status, color in [
            ("FRESH", "green"),
            ("DECAYING (>21 Days)", "yellow"),
            ("STALE (>45 Days)", "red"),
        ]:
            item = LedgerItem(
                opportunity_id=1,
                theme="T",
                personas_affected=[],
                opportunity="O",
                status=status,
                status_color=color,
                days_old=0,
                is_cross_functional=False,
                evidence=[],
            )
            assert item.status == status
            assert item.status_color == color


class TestPendingLlmUsage:
    def test_create(self):
        usage = PendingLlmUsage(
            model_name="gemini-2.5-pro",
            operation="synthesis",
            prompt_tokens=1500,
            output_tokens=250,
            total_tokens=1750,
        )
        assert usage.model_name == "gemini-2.5-pro"
        assert usage.total_tokens == 1750

    def test_all_operations(self):
        for op in ["synthesis", "dedupe", "prep"]:
            usage = PendingLlmUsage(
                model_name="gemini-2.5-flash",
                operation=op,
                prompt_tokens=100,
                output_tokens=50,
                total_tokens=150,
            )
            assert usage.operation == op


class TestLlmUsageItem:
    def test_create(self):
        item = LlmUsageItem(
            id=1,
            model_name="gemini-2.5-flash",
            operation="dedupe",
            interview_id=3,
            prompt_tokens=200,
            output_tokens=100,
            total_tokens=300,
            created_at="2025-01-15 14:30",
        )
        assert item.id == 1
        assert item.total_tokens == 300
        assert item.created_at == "2025-01-15 14:30"


class TestInterviewHistoryItem:
    def test_create_with_defaults(self):
        item = InterviewHistoryItem(
            interview_id=7,
            persona="Enterprise User",
            date_logged="2025-02-01 10:00",
            snippet="The feature we use most is...",
        )
        assert item.interview_id == 7
        assert item.persona_color == "gray"
        assert item.interview_date == ""
        assert item.duration_minutes == 0
        assert item.participants == ""

    def test_create_with_all_metadata(self):
        item = InterviewHistoryItem(
            interview_id=8,
            persona="SMB Owner",
            persona_color="green",
            date_logged="2025-02-10 15:00",
            snippet="We love the product but...",
            interview_date="2025-02-09",
            duration_minutes=45,
            participants="Alice, Bob",
        )
        assert item.persona_color == "green"
        assert item.duration_minutes == 45
        assert item.participants == "Alice, Bob"
        assert item.interview_date == "2025-02-09"


class TestPrepOppItem:
    def test_create_with_required_fields(self):
        item = PrepOppItem(
            id=1, theme="Workflow", statement="Users can't batch-export invoices"
        )
        assert item.id == 1
        assert item.theme == "Workflow"
        assert item.statement == "Users can't batch-export invoices"

    def test_selected_defaults_to_false(self):
        item = PrepOppItem(id=1, theme="T", statement="S")
        assert item.selected is False

    def test_selected_can_be_true(self):
        item = PrepOppItem(id=1, theme="T", statement="S", selected=True)
        assert item.selected is True

    def test_id_is_int(self):
        item = PrepOppItem(id=99, theme="T", statement="S")
        assert isinstance(item.id, int)

    def test_theme_and_statement_are_strings(self):
        item = PrepOppItem(id=1, theme="Onboarding", statement="Setup takes too long")
        assert isinstance(item.theme, str)
        assert isinstance(item.statement, str)

    def test_multiple_items_are_independent(self):
        a = PrepOppItem(id=1, theme="T", statement="S", selected=True)
        b = PrepOppItem(id=2, theme="T", statement="S", selected=False)
        assert a.selected is True
        assert b.selected is False


class TestPrepExperimentItem:
    def test_create_with_all_fields(self):
        item = PrepExperimentItem(
            id=3,
            opp_id=10,
            solution_name="Auto-Suggest",
            experiment_name="Fake Door Test",
            assumption="Users will click the new button",
        )
        assert item.id == 3
        assert item.opp_id == 10
        assert item.solution_name == "Auto-Suggest"
        assert item.experiment_name == "Fake Door Test"
        assert item.assumption == "Users will click the new button"

    def test_selected_defaults_to_false(self):
        item = PrepExperimentItem(
            id=1, opp_id=1, solution_name="S", experiment_name="E", assumption="A"
        )
        assert item.selected is False

    def test_selected_can_be_true(self):
        item = PrepExperimentItem(
            id=1,
            opp_id=1,
            solution_name="S",
            experiment_name="E",
            assumption="A",
            selected=True,
        )
        assert item.selected is True

    def test_opp_id_links_to_parent_opportunity(self):
        item = PrepExperimentItem(
            id=5, opp_id=42, solution_name="S", experiment_name="E", assumption="A"
        )
        assert item.opp_id == 42

    def test_multiple_items_are_independent(self):
        a = PrepExperimentItem(
            id=1,
            opp_id=10,
            solution_name="S",
            experiment_name="E",
            assumption="A",
            selected=True,
        )
        b = PrepExperimentItem(
            id=2,
            opp_id=10,
            solution_name="S",
            experiment_name="E",
            assumption="A",
            selected=False,
        )
        assert a.selected is True
        assert b.selected is False


# ---------------------------------------------------------------------------
# DashboardBarItem (home dashboard weekly sparkline)
# ---------------------------------------------------------------------------


class TestDashboardBarItem:
    def test_create(self):
        bar = DashboardBarItem(week_label="Jan 20", count=3, height_css="36px")
        assert bar.week_label == "Jan 20"
        assert bar.count == 3
        assert bar.height_css == "36px"

    def test_height_css_default(self):
        bar = DashboardBarItem(week_label="Feb 03", count=0)
        assert bar.height_css == "0px"

    def test_zero_count_bar(self):
        bar = DashboardBarItem(week_label="Mar 10", count=0, height_css="0px")
        assert bar.count == 0
        assert bar.height_css == "0px"

    def test_max_height_bar(self):
        bar = DashboardBarItem(week_label="Apr 07", count=5, height_css="48px")
        assert bar.count == 5
        assert bar.height_css == "48px"

    def test_week_label_preserved(self):
        for label in ["Jan 05", "Feb 12", "Mar 19", "Dec 30"]:
            bar = DashboardBarItem(week_label=label, count=1, height_css="10px")
            assert bar.week_label == label

    def test_count_is_int(self):
        bar = DashboardBarItem(week_label="Jan 01", count=7, height_css="48px")
        assert isinstance(bar.count, int)

    def test_height_css_is_str(self):
        bar = DashboardBarItem(week_label="Jan 01", count=2, height_css="24px")
        assert isinstance(bar.height_css, str)


# ---------------------------------------------------------------------------
# RecentInterviewItem (home dashboard activity feed)
# ---------------------------------------------------------------------------


class TestRecentInterviewItem:
    def test_create(self):
        item = RecentInterviewItem(
            interview_id=42,
            persona="Enterprise Buyer",
            persona_color="blue",
            date_str="2026-02-28",
            quote_count=5,
        )
        assert item.interview_id == 42
        assert item.persona == "Enterprise Buyer"
        assert item.persona_color == "blue"
        assert item.date_str == "2026-02-28"
        assert item.quote_count == 5

    def test_zero_quotes(self):
        item = RecentInterviewItem(
            interview_id=1,
            persona="SMB Owner",
            persona_color="green",
            date_str="2026-01-01",
            quote_count=0,
        )
        assert item.quote_count == 0

    def test_all_persona_colors(self):
        colors = [
            "red",
            "amber",
            "green",
            "blue",
            "violet",
            "crimson",
        ]
        for color in colors:
            item = RecentInterviewItem(
                interview_id=1,
                persona="User",
                persona_color=color,
                date_str="2026-01-01",
                quote_count=1,
            )
            assert item.persona_color == color

    def test_interview_id_is_int(self):
        item = RecentInterviewItem(
            interview_id=99,
            persona="P",
            persona_color="blue",
            date_str="2026-01-01",
            quote_count=3,
        )
        assert isinstance(item.interview_id, int)

    def test_date_str_formats(self):
        for date_str in ["2026-01-15", "2025-12-31", "2026-03-01"]:
            item = RecentInterviewItem(
                interview_id=1,
                persona="P",
                persona_color="blue",
                date_str=date_str,
                quote_count=0,
            )
            assert item.date_str == date_str


# ---------------------------------------------------------------------------
# ParticipantItem (CRM)
# ---------------------------------------------------------------------------


class TestParticipantItem:
    def test_create_customer(self):
        item = ParticipantItem(
            id=1,
            name="Alice Chen",
            persona_name="VP of Engineering",
            persona_color="blue",
            is_team_member=False,
            segment="Enterprise",
            recruited_via="LinkedIn",
            notes="",
        )
        assert item.id == 1
        assert item.name == "Alice Chen"
        assert item.is_team_member is False

    def test_create_team_member(self):
        item = ParticipantItem(
            id=2,
            name="Bob Smith",
            persona_name="",
            persona_color="gray",
            is_team_member=True,
            segment="",
            recruited_via="",
            notes="",
        )
        assert item.is_team_member is True

    def test_defaults(self):
        item = ParticipantItem(
            id=3,
            name="Charlie",
            segment="SMB",
            recruited_via="Referral",
            notes="",
        )
        assert item.persona_name == ""
        assert item.persona_color == "gray"
        assert item.is_team_member is False
        assert item.interview_count == 0
        assert item.last_interviewed == ""

    def test_interview_count_and_last_interviewed(self):
        item = ParticipantItem(
            id=4,
            name="Dana",
            segment="",
            recruited_via="",
            notes="",
            interview_count=7,
            last_interviewed="2026-02-15",
        )
        assert item.interview_count == 7
        assert item.last_interviewed == "2026-02-15"

    def test_notes_preserved(self):
        notes = "Key customer. Runs a 50-person team. Very opinionated about UX."
        item = ParticipantItem(
            id=5,
            name="Eve",
            segment="",
            recruited_via="",
            notes=notes,
        )
        assert item.notes == notes


# ---------------------------------------------------------------------------
# DetailParticipantItem (read-only chip in interview detail view)
# ---------------------------------------------------------------------------


class TestDetailParticipantItem:
    def test_create_customer(self):
        item = DetailParticipantItem(name="Alice Chen")
        assert item.name == "Alice Chen"
        assert item.is_team_member is False

    def test_create_team_member(self):
        item = DetailParticipantItem(name="Bob Smith", is_team_member=True)
        assert item.is_team_member is True

    def test_is_team_member_defaults_false(self):
        item = DetailParticipantItem(name="Anyone")
        assert item.is_team_member is False

    def test_name_is_str(self):
        item = DetailParticipantItem(name="Carol")
        assert isinstance(item.name, str)


# ---------------------------------------------------------------------------
# PendingParticipantItem (role editor during synthesis review)
# ---------------------------------------------------------------------------


class TestPendingParticipantItem:
    def test_create_with_defaults(self):
        item = PendingParticipantItem(index=0, name="Alice")
        assert item.index == 0
        assert item.name == "Alice"
        assert item.role == "interviewee"

    def test_role_interviewer(self):
        item = PendingParticipantItem(index=1, name="Bob", role="interviewer")
        assert item.role == "interviewer"

    def test_index_tracks_position(self):
        items = [PendingParticipantItem(index=i, name=f"Person {i}") for i in range(5)]
        for i, item in enumerate(items):
            assert item.index == i

    def test_both_valid_roles(self):
        for role in ["interviewee", "interviewer"]:
            item = PendingParticipantItem(index=0, name="N", role=role)
            assert item.role == role


# ---------------------------------------------------------------------------
# ExperimentItem — new description / success_metric fields + start_edit logic
# ---------------------------------------------------------------------------

_STANDARD_METHODS = {
    "Prototype Interview",
    "Fake Door",
    "A/B Test",
    "Usability Test",
    "Survey",
    "Other",
}


def _resolve_method_for_edit(method: str):
    """
    Pure-function replica of the method-resolution logic in
    LedgerStateMixin.start_edit_experiment().

    Returns (new_experiment_method, new_experiment_method_other).
    """
    if method in _STANDARD_METHODS:
        return method, ""
    else:
        return "Other", method


class TestExperimentItemNewFields:
    def _make_exp(self, **kwargs):
        defaults = dict(
            id=1,
            solution_id=1,
            solution_name="S",
            name="N",
            assumption="A",
            description="",
            success_metric="",
            method="Fake Door",
            status="Draft",
            signal="Pending",
            evidence_notes="",
        )
        defaults.update(kwargs)
        return ExperimentItem(**defaults)

    def test_description_field_accessible(self):
        exp = self._make_exp(description="Run a 2-week fake door test")
        assert exp.description == "Run a 2-week fake door test"

    def test_success_metric_field_accessible(self):
        exp = self._make_exp(success_metric="Click-through rate > 5%")
        assert exp.success_metric == "Click-through rate > 5%"

    def test_description_defaults_to_empty_string(self):
        exp = self._make_exp()
        assert exp.description == ""

    def test_success_metric_defaults_to_empty_string(self):
        exp = self._make_exp()
        assert exp.success_metric == ""

    def test_both_fields_are_strings(self):
        exp = self._make_exp(description="desc", success_metric="metric")
        assert isinstance(exp.description, str)
        assert isinstance(exp.success_metric, str)

    # --- start_edit_experiment method-resolution logic ---

    def test_standard_method_returned_directly(self):
        for method in [
            "Prototype Interview",
            "Fake Door",
            "A/B Test",
            "Usability Test",
            "Survey",
            "Other",
        ]:
            resolved, other = _resolve_method_for_edit(method)
            assert resolved == method
            assert other == ""

    def test_custom_method_sets_other_sentinel(self):
        resolved, other = _resolve_method_for_edit("Dogfooding")
        assert resolved == "Other"
        assert other == "Dogfooding"

    def test_empty_custom_method_uses_other_sentinel(self):
        resolved, other = _resolve_method_for_edit("")
        assert resolved == "Other"
        assert other == ""

    def test_whitespace_custom_method_preserved_in_other(self):
        # Whitespace is not a standard method, so it goes to the free-text slot.
        resolved, other = _resolve_method_for_edit("   ")
        assert resolved == "Other"
        assert other == "   "
