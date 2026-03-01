"""Unit tests for rx.Base data classes used for UI state.

These classes carry data between the backend state and the frontend.
Tests ensure correct instantiation, field types, and defaults.
"""
import pytest

# conftest.py has mocked google.generativeai before this import.
from cont_synth.state.core import (
    ExperimentItem,
    InterviewHistoryItem,
    LedgerItem,
    LlmUsageItem,
    OppDetailSolution,
    OutcomeItem,
    PendingLlmUsage,
    PendingOppItem,
    PersonaBadge,
    ProductItem,
    QuoteItem,
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
        colors = ["blue", "purple", "orange", "green", "pink", "teal", "ruby", "iris", "indigo"]
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
        quote = QuoteItem(interview_id=1, persona_name="U", persona_color="blue", text=text)
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
                id=1, solution_id=1, solution_name="S",
                name="N", assumption="A", method=method,
                status="Draft", signal="Pending", evidence_notes="",
            )
            assert exp.method == method

    def test_all_statuses(self):
        for status in ["Draft", "Running", "Concluded"]:
            exp = ExperimentItem(
                id=1, solution_id=1, solution_name="S",
                name="N", assumption="A", method="Fake Door",
                status=status, signal="Pending", evidence_notes="",
            )
            assert exp.status == status

    def test_all_signals(self):
        for signal in ["Pending", "Validated", "Invalidated"]:
            exp = ExperimentItem(
                id=1, solution_id=1, solution_name="S",
                name="N", assumption="A", method="A/B Test",
                status="Concluded", signal=signal, evidence_notes="",
            )
            assert exp.signal == signal


class TestOppDetailSolution:
    def test_create_with_defaults(self):
        sol = OppDetailSolution(
            id=5, name="Redesign flow", description="Full UX overhaul", status="Ideation"
        )
        assert sol.experiments == []
        assert sol.parent_id is None
        assert sol.indent_level == 0

    def test_create_with_experiments(self):
        exp = ExperimentItem(
            id=1, solution_id=5, solution_name="Redesign flow",
            name="Fake Door", assumption="Users want it", method="Fake Door",
            status="Draft", signal="Pending", evidence_notes="",
        )
        sol = OppDetailSolution(
            id=5, name="Redesign flow", description="", status="Testing",
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
            PendingOppItem(index=i, opportunity_statement=f"Need {i}", theme="T", source_quote="Q")
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
            opportunity_id=2, theme="T", personas_affected=[],
            opportunity="O", status="FRESH", status_color="green",
            days_old=0, is_cross_functional=False, evidence=[],
        )
        assert item.parent_id == -1

    def test_create_with_full_data(self):
        badge = PersonaBadge(name="Admin", color="blue")
        quote = QuoteItem(interview_id=1, persona_name="Admin", persona_color="blue", text="Q")
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
                opportunity_id=1, theme="T", personas_affected=[],
                opportunity="O", status=status, status_color=color,
                days_old=0, is_cross_functional=False, evidence=[],
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
