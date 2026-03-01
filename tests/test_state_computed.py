"""Tests for logic that mirrors the @rx.var computed properties on State.

These tests verify the *logic* of computed properties without needing the
Reflex runtime.  The logic is replicated inline and exercised independently.
"""
import pytest

from cont_synth.state.core import (
    LlmUsageItem,
    PendingOppItem,
    PersonaBadge,
    ProductItem,
    QuoteItem,
)


# ---------------------------------------------------------------------------
# active_product_name logic
# ---------------------------------------------------------------------------

def _active_product_name(products: list[ProductItem], active_id: str) -> str:
    """Replica of State.active_product_name @rx.var."""
    active = next((p for p in products if str(p.id) == active_id), None)
    return active.name if active else "Select workspace"


class TestActiveProductName:
    def test_returns_matching_product_name(self):
        products = [ProductItem(id=1, name="Workspace A"), ProductItem(id=2, name="Workspace B")]
        assert _active_product_name(products, "2") == "Workspace B"

    def test_first_product_selected(self):
        products = [ProductItem(id=1, name="Only Workspace")]
        assert _active_product_name(products, "1") == "Only Workspace"

    def test_missing_id_returns_placeholder(self):
        products = [ProductItem(id=1, name="Only")]
        assert _active_product_name(products, "999") == "Select workspace"

    def test_empty_product_list(self):
        assert _active_product_name([], "1") == "Select workspace"

    def test_id_as_string_matches(self):
        """active_product_id is stored as a string in state."""
        products = [ProductItem(id=42, name="WS")]
        assert _active_product_name(products, "42") == "WS"


# ---------------------------------------------------------------------------
# llm_total_tokens / llm_synthesis_count / llm_dedupe_count
# ---------------------------------------------------------------------------

def _make_log(operation: str, total_tokens: int) -> LlmUsageItem:
    return LlmUsageItem(
        id=1,
        model_name="gemini-2.5-flash",
        operation=operation,
        interview_id=0,
        prompt_tokens=0,
        output_tokens=0,
        total_tokens=total_tokens,
        created_at="",
    )


class TestLlmAggregates:
    def test_total_tokens_sum(self):
        logs = [_make_log("synthesis", 1500), _make_log("dedupe", 300), _make_log("prep", 200)]
        total = sum(log.total_tokens for log in logs)
        assert total == 2000

    def test_total_tokens_empty(self):
        assert sum(log.total_tokens for log in []) == 0

    def test_synthesis_count(self):
        logs = [
            _make_log("synthesis", 100),
            _make_log("dedupe", 50),
            _make_log("synthesis", 80),
            _make_log("prep", 30),
        ]
        count = sum(1 for log in logs if log.operation == "synthesis")
        assert count == 2

    def test_dedupe_count(self):
        logs = [_make_log("synthesis", 100), _make_log("dedupe", 50), _make_log("dedupe", 60)]
        count = sum(1 for log in logs if log.operation == "dedupe")
        assert count == 2

    def test_counts_independent(self):
        logs = [
            _make_log("synthesis", 1),
            _make_log("synthesis", 1),
            _make_log("dedupe", 1),
            _make_log("prep", 1),
        ]
        assert sum(1 for l in logs if l.operation == "synthesis") == 2
        assert sum(1 for l in logs if l.operation == "dedupe") == 1
        assert sum(1 for l in logs if l.operation == "prep") == 1


# ---------------------------------------------------------------------------
# selected_opp_count
# ---------------------------------------------------------------------------

def _selected_opp_count(opps: list[PendingOppItem]) -> int:
    """Replica of State.selected_opp_count @rx.var."""
    return sum(1 for opp in opps if opp.selected)


class TestSelectedOppCount:
    def test_all_selected(self):
        opps = [
            PendingOppItem(index=i, opportunity_statement=f"Need {i}", theme="T", source_quote="Q")
            for i in range(5)
        ]
        assert _selected_opp_count(opps) == 5

    def test_none_selected(self):
        opps = [
            PendingOppItem(
                index=i, opportunity_statement=f"Need {i}", theme="T", source_quote="Q",
                selected=False,
            )
            for i in range(3)
        ]
        assert _selected_opp_count(opps) == 0

    def test_partial_selection(self):
        opps = [
            PendingOppItem(index=0, opportunity_statement="A", theme="T", source_quote="Q", selected=True),
            PendingOppItem(index=1, opportunity_statement="B", theme="T", source_quote="Q", selected=False),
            PendingOppItem(index=2, opportunity_statement="C", theme="T", source_quote="Q", selected=True),
        ]
        assert _selected_opp_count(opps) == 2

    def test_empty_list(self):
        assert _selected_opp_count([]) == 0


# ---------------------------------------------------------------------------
# pending_synthesis_participants_str
# ---------------------------------------------------------------------------

def _participants_str(participants: list[str]) -> str:
    """Replica of State.pending_synthesis_participants_str @rx.var."""
    return ", ".join(participants)


class TestParticipantsStr:
    def test_empty_list(self):
        assert _participants_str([]) == ""

    def test_single_participant(self):
        assert _participants_str(["Alice"]) == "Alice"

    def test_multiple_participants(self):
        assert _participants_str(["Alice", "Bob", "Charlie"]) == "Alice, Bob, Charlie"

    def test_two_participants(self):
        assert _participants_str(["X", "Y"]) == "X, Y"


# ---------------------------------------------------------------------------
# quote_position / has_prev_quote / has_next_quote
# ---------------------------------------------------------------------------

def _quote_position(quotes: list, index: int) -> str:
    """Replica of State.quote_position @rx.var."""
    if not quotes:
        return "0 of 0"
    return f"{index + 1} of {len(quotes)}"


def _has_prev(index: int) -> bool:
    return index > 0


def _has_next(index: int, quotes: list) -> bool:
    return index < len(quotes) - 1


class TestQuoteNavigation:
    def test_position_empty_quotes(self):
        assert _quote_position([], 0) == "0 of 0"

    def test_position_first_of_three(self):
        quotes = ["q1", "q2", "q3"]
        assert _quote_position(quotes, 0) == "1 of 3"

    def test_position_last_of_three(self):
        quotes = ["q1", "q2", "q3"]
        assert _quote_position(quotes, 2) == "3 of 3"

    def test_has_prev_at_zero(self):
        assert _has_prev(0) is False

    def test_has_prev_at_one(self):
        assert _has_prev(1) is True

    def test_has_next_at_last(self):
        quotes = ["q1", "q2"]
        assert _has_next(1, quotes) is False

    def test_has_next_not_at_last(self):
        quotes = ["q1", "q2", "q3"]
        assert _has_next(0, quotes) is True
        assert _has_next(1, quotes) is True

    def test_all_positions(self):
        quotes = list(range(4))
        for i in range(len(quotes)):
            pos = _quote_position(quotes, i)
            assert pos == f"{i + 1} of 4"


# ---------------------------------------------------------------------------
# active_quote fallback (replica of State.active_quote @rx.var)
# ---------------------------------------------------------------------------

class TestActiveQuote:
    def test_fallback_when_empty(self):
        """When no quotes exist, return a placeholder."""
        quotes = []
        if not quotes:
            result = QuoteItem(
                interview_id=0, persona_name="", persona_color="gray",
                text="No evidence snippets found."
            )
        else:
            idx = max(0, min(0, len(quotes) - 1))
            result = quotes[idx]
        assert result.text == "No evidence snippets found."

    def test_clamped_index(self):
        """Index is clamped to valid range."""
        quotes = [
            QuoteItem(interview_id=1, persona_name="A", persona_color="blue", text="First"),
            QuoteItem(interview_id=2, persona_name="B", persona_color="red", text="Second"),
        ]
        # Index beyond range → clamped to last
        idx = max(0, min(99, len(quotes) - 1))
        assert quotes[idx].text == "Second"

        # Negative index → clamped to 0
        idx = max(0, min(-5, len(quotes) - 1))
        assert quotes[idx].text == "First"
