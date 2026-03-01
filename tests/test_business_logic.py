"""Unit tests for pure business-logic functions extracted from state mixins.

These tests cover logic that lives *inside* state methods but is fully
deterministic and has no Reflex / database dependencies.
"""
import json
from dataclasses import dataclass
from typing import Optional

import pytest


# ---------------------------------------------------------------------------
# Evidence status computation (from LedgerStateMixin.load_ledger)
# ---------------------------------------------------------------------------

def _compute_status(days_old: int) -> tuple[str, str]:
    """Replica of the inline status logic in load_ledger()."""
    if days_old > 45:
        return "STALE (>45 Days)", "red"
    elif days_old > 21:
        return "DECAYING (>21 Days)", "yellow"
    else:
        return "FRESH", "green"


class TestEvidenceStatus:
    @pytest.mark.parametrize(
        "days, expected_status, expected_color",
        [
            (0, "FRESH", "green"),
            (1, "FRESH", "green"),
            (10, "FRESH", "green"),
            (20, "FRESH", "green"),
            (21, "FRESH", "green"),          # Boundary: NOT > 21, so FRESH
            (22, "DECAYING (>21 Days)", "yellow"),  # Just above 21
            (30, "DECAYING (>21 Days)", "yellow"),
            (44, "DECAYING (>21 Days)", "yellow"),
            (45, "DECAYING (>21 Days)", "yellow"),  # Boundary: NOT > 45
            (46, "STALE (>45 Days)", "red"),        # Just above 45
            (60, "STALE (>45 Days)", "red"),
            (100, "STALE (>45 Days)", "red"),
            (365, "STALE (>45 Days)", "red"),
        ],
    )
    def test_status_thresholds(self, days, expected_status, expected_color):
        status, color = _compute_status(days)
        assert status == expected_status
        assert color == expected_color

    def test_fresh_zone(self):
        for days in range(22):
            status, color = _compute_status(days)
            assert status == "FRESH"
            assert color == "green"

    def test_decaying_zone(self):
        for days in range(22, 46):
            status, color = _compute_status(days)
            assert status == "DECAYING (>21 Days)"
            assert color == "yellow"

    def test_stale_zone(self):
        for days in [46, 50, 90, 180, 365]:
            status, color = _compute_status(days)
            assert status == "STALE (>45 Days)"
            assert color == "red"


# ---------------------------------------------------------------------------
# Persona color assignment (from InterviewStateMixin._persona_color)
# ---------------------------------------------------------------------------

_PERSONA_COLORS = [
    "blue", "purple", "orange", "green", "pink",
    "teal", "ruby", "iris", "indigo",
]


def _persona_color(name: str) -> str:
    """Replica of InterviewStateMixin._persona_color()."""
    idx = sum(ord(c) for c in name) % len(_PERSONA_COLORS)
    return _PERSONA_COLORS[idx]


class TestPersonaColor:
    def test_returns_valid_color(self):
        names = ["Alice", "Bob", "Customer", "Admin", "PowerUser", "Enterprise"]
        for name in names:
            assert _persona_color(name) in _PERSONA_COLORS

    def test_deterministic(self):
        name = "ConsistentUser"
        assert _persona_color(name) == _persona_color(name)

    def test_different_names_show_variation(self):
        """At least some name variation produces different colors."""
        colors = {_persona_color(f"User{i}") for i in range(30)}
        assert len(colors) > 1

    @pytest.mark.parametrize("name", ["Alice", "Bob", "Charlie", "Dave", "Eve", "Frank"])
    def test_color_always_in_palette(self, name):
        assert _persona_color(name) in _PERSONA_COLORS

    def test_empty_name_returns_valid_color(self):
        # sum(ord) of "" = 0, 0 % 9 = 0 → first color
        assert _persona_color("") == _PERSONA_COLORS[0]

    def test_color_index_wraps_around(self):
        """Index always stays within bounds no matter how long the name."""
        long_name = "A" * 10_000
        color = _persona_color(long_name)
        assert color in _PERSONA_COLORS


# ---------------------------------------------------------------------------
# Transcript snippet (from InterviewStateMixin.load_history)
# ---------------------------------------------------------------------------

def _make_snippet(transcript: str) -> str:
    """Replica of the snippet logic in load_history()."""
    return transcript[:80] + "..." if transcript else "No transcript."


class TestTranscriptSnippet:
    def test_short_transcript_gets_ellipsis(self):
        result = _make_snippet("Short text.")
        assert result == "Short text...."

    def test_long_transcript_truncated_at_80(self):
        result = _make_snippet("A" * 100)
        assert result == "A" * 80 + "..."
        assert len(result) == 83

    def test_exactly_80_chars_gets_ellipsis(self):
        result = _make_snippet("A" * 80)
        assert result == "A" * 80 + "..."

    def test_empty_transcript(self):
        assert _make_snippet("") == "No transcript."

    def test_79_chars(self):
        result = _make_snippet("A" * 79)
        assert result == "A" * 79 + "..."

    def test_newlines_preserved(self):
        transcript = "Line one\nLine two\nLine three"
        result = _make_snippet(transcript)
        assert result.startswith("Line one\nLine two")


# ---------------------------------------------------------------------------
# Participants parsing (from InterviewStateMixin.load_history)
# ---------------------------------------------------------------------------

def _parse_participants(participants_raw: Optional[str]) -> str:
    """Replica of participants parsing logic in load_history()."""
    if not participants_raw:
        return ""
    try:
        return ", ".join(json.loads(participants_raw))
    except Exception:
        return participants_raw


class TestParticipantsParsing:
    def test_none_input(self):
        assert _parse_participants(None) == ""

    def test_empty_string(self):
        assert _parse_participants("") == ""

    def test_valid_json_array(self):
        result = _parse_participants('["Alice", "Bob", "Charlie"]')
        assert result == "Alice, Bob, Charlie"

    def test_single_participant(self):
        assert _parse_participants('["Solo User"]') == "Solo User"

    def test_empty_json_array(self):
        assert _parse_participants("[]") == ""

    def test_invalid_json_returns_raw(self):
        raw = "Alice, Bob"
        assert _parse_participants(raw) == "Alice, Bob"

    def test_malformed_json_returns_raw(self):
        raw = "[not valid json"
        assert _parse_participants(raw) == raw

    def test_preserves_spaces_in_names(self):
        result = _parse_participants('["Mary Jane Watson", "Peter Parker"]')
        assert result == "Mary Jane Watson, Peter Parker"


# ---------------------------------------------------------------------------
# Opportunity flattening algorithm (from LedgerStateMixin.load_ledger)
# ---------------------------------------------------------------------------

@dataclass
class _MockOpp:
    id: int
    parent_id: Optional[int] = None


def _flatten_opportunities(opportunities: list) -> list:
    """Replica of the bulletproof flattening algorithm from load_ledger()."""
    opp_dict = {opp.id: opp for opp in opportunities}
    opp_children_map: dict = {}
    opp_top_level: list = []

    for opp in opportunities:
        if opp.parent_id and opp.parent_id in opp_dict:
            opp_children_map.setdefault(opp.parent_id, []).append(opp)
        else:
            opp_top_level.append(opp)

    flat_opps: list = []
    visited_nodes: set = set()

    def append_opp_children(opp_id: int, current_level: int) -> None:
        if opp_id in visited_nodes:
            return
        visited_nodes.add(opp_id)
        for child in opp_children_map.get(opp_id, []):
            if child.id not in visited_nodes:
                flat_opps.append((child, current_level))
                append_opp_children(child.id, current_level + 1)

    for opp in opp_top_level:
        if opp.id not in visited_nodes:
            flat_opps.append((opp, 0))
            append_opp_children(opp.id, 1)

    # Recovery: orphaned / cycled nodes
    for opp in opportunities:
        if opp.id not in visited_nodes:
            flat_opps.append((opp, 0))
            append_opp_children(opp.id, 1)

    return flat_opps


class TestOpportunityFlattening:
    def test_empty_list(self):
        assert _flatten_opportunities([]) == []

    def test_single_top_level(self):
        opp = _MockOpp(id=1)
        result = _flatten_opportunities([opp])
        assert result == [(opp, 0)]

    def test_simple_parent_child(self):
        parent = _MockOpp(id=1)
        child = _MockOpp(id=2, parent_id=1)
        result = _flatten_opportunities([parent, child])
        assert result[0] == (parent, 0)
        assert result[1] == (child, 1)

    def test_three_level_hierarchy(self):
        root = _MockOpp(id=1)
        mid = _MockOpp(id=2, parent_id=1)
        leaf = _MockOpp(id=3, parent_id=2)
        result = _flatten_opportunities([root, mid, leaf])
        assert result[0] == (root, 0)
        assert result[1] == (mid, 1)
        assert result[2] == (leaf, 2)

    def test_multiple_top_level_items(self):
        opps = [_MockOpp(id=i) for i in range(1, 5)]
        result = _flatten_opportunities(opps)
        assert len(result) == 4
        assert all(level == 0 for _, level in result)

    def test_orphan_with_missing_parent_is_top_level(self):
        """parent_id points to a non-existent ID → treated as top-level."""
        orphan = _MockOpp(id=1, parent_id=999)
        result = _flatten_opportunities([orphan])
        assert result == [(orphan, 0)]

    def test_cycle_a_to_b_to_a(self):
        """Cyclic dependency A→B→A should not infinite-loop; both appear once."""
        a = _MockOpp(id=1, parent_id=2)
        b = _MockOpp(id=2, parent_id=1)
        result = _flatten_opportunities([a, b])
        ids = [opp.id for opp, _ in result]
        assert sorted(ids) == [1, 2]
        assert len(ids) == 2

    def test_cycle_results_in_mixed_levels(self):
        a = _MockOpp(id=1, parent_id=2)
        b = _MockOpp(id=2, parent_id=1)
        result = _flatten_opportunities([a, b])
        levels = [level for _, level in result]
        assert 0 in levels
        assert 1 in levels

    def test_all_nodes_appear_exactly_once(self):
        opps = [
            _MockOpp(id=1),
            _MockOpp(id=2, parent_id=1),
            _MockOpp(id=3, parent_id=1),
            _MockOpp(id=4, parent_id=2),
            _MockOpp(id=5),
        ]
        result = _flatten_opportunities(opps)
        ids = [opp.id for opp, _ in result]
        assert sorted(ids) == [1, 2, 3, 4, 5]
        assert len(set(ids)) == 5  # No duplicates

    def test_children_immediately_follow_parent(self):
        """Depth-first order: grandchild appears right after child."""
        root = _MockOpp(id=1)
        child = _MockOpp(id=2, parent_id=1)
        grandchild = _MockOpp(id=3, parent_id=2)
        sibling = _MockOpp(id=4, parent_id=1)
        result = _flatten_opportunities([root, child, grandchild, sibling])
        ids = [opp.id for opp, _ in result]
        # grandchild (3) must come immediately after child (2)
        assert ids.index(3) == ids.index(2) + 1

    def test_siblings_all_same_level(self):
        root = _MockOpp(id=1)
        children = [_MockOpp(id=i, parent_id=1) for i in range(2, 6)]
        result = _flatten_opportunities([root] + children)
        child_levels = [level for opp, level in result if opp.id != 1]
        assert all(l == 1 for l in child_levels)


# ---------------------------------------------------------------------------
# Selected opportunity count (from State.selected_opp_count @rx.var)
# ---------------------------------------------------------------------------

class TestSelectedOppCount:
    def _count_selected(self, opps) -> int:
        return sum(1 for opp in opps if opp["selected"])

    def test_all_selected(self):
        opps = [{"selected": True} for _ in range(5)]
        assert self._count_selected(opps) == 5

    def test_none_selected(self):
        opps = [{"selected": False} for _ in range(4)]
        assert self._count_selected(opps) == 0

    def test_partial_selection(self):
        opps = [
            {"selected": True},
            {"selected": False},
            {"selected": True},
            {"selected": True},
        ]
        assert self._count_selected(opps) == 3

    def test_empty_list(self):
        assert self._count_selected([]) == 0
