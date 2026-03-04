"""Unit tests for pure business-logic functions extracted from state mixins.

These tests cover logic that lives *inside* state methods but is fully
deterministic and has no Reflex / database dependencies.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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
    "red",
    "amber",
    "green",
    "blue",
    "violet",
    "crimson",
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


# ---------------------------------------------------------------------------
# Opportunity priority score (LedgerItem.priority_score = impact + sat_gap + min(evidence, 5))
# ---------------------------------------------------------------------------

def _priority_score(impact: int, sat_gap: int, evidence_count: int) -> int:
    """Replica of the priority_score calculation in LedgerStateMixin.load_ledger()."""
    return impact + sat_gap + min(evidence_count, 5)


class TestOpportunityPriorityScore:
    def test_all_zeros(self):
        assert _priority_score(0, 0, 0) == 0

    def test_max_scores(self):
        # impact=5, sat_gap=5, evidence capped at 5 → max = 15
        assert _priority_score(5, 5, 100) == 15

    def test_evidence_capped_at_five(self):
        assert _priority_score(0, 0, 5) == 5
        assert _priority_score(0, 0, 6) == 5
        assert _priority_score(0, 0, 99) == 5

    def test_evidence_below_cap_not_clamped(self):
        for n in range(6):
            assert _priority_score(0, 0, n) == n

    def test_impact_only(self):
        for i in range(1, 6):
            assert _priority_score(i, 0, 0) == i

    def test_sat_gap_only(self):
        for s in range(1, 6):
            assert _priority_score(0, s, 0) == s

    def test_additive(self):
        assert _priority_score(3, 4, 2) == 3 + 4 + 2
        assert _priority_score(2, 2, 3) == 2 + 2 + 3

    def test_unrated_scores_zero(self):
        # 0 = unrated, contributes nothing to the score
        assert _priority_score(0, 0, 0) == 0

    @pytest.mark.parametrize("impact,sat_gap,evidence,expected", [
        (1, 1, 1, 3),
        (5, 5, 5, 15),
        (3, 0, 0, 3),
        (0, 4, 10, 9),  # evidence capped: 0+4+5=9
        (5, 5, 0, 10),
    ])
    def test_parametrized(self, impact, sat_gap, evidence, expected):
        assert _priority_score(impact, sat_gap, evidence) == expected


# ---------------------------------------------------------------------------
# Filtered participants (State.filtered_participants @rx.var)
# ---------------------------------------------------------------------------

@dataclass
class _MockParticipant:
    id: int
    name: str
    is_team_member: bool = False


def _filter_participants(participants: list, show_team_members: bool) -> list:
    """Replica of State.filtered_participants @rx.var."""
    if show_team_members:
        return participants
    return [p for p in participants if not p.is_team_member]


class TestFilteredParticipants:
    def _make_mix(self):
        return [
            _MockParticipant(id=1, name="Alice", is_team_member=False),
            _MockParticipant(id=2, name="Bob", is_team_member=True),
            _MockParticipant(id=3, name="Charlie", is_team_member=False),
            _MockParticipant(id=4, name="Diana", is_team_member=True),
        ]

    def test_hide_team_members_excludes_interviewers(self):
        result = _filter_participants(self._make_mix(), show_team_members=False)
        assert all(not p.is_team_member for p in result)
        assert len(result) == 2
        assert {p.id for p in result} == {1, 3}

    def test_show_team_members_returns_all(self):
        participants = self._make_mix()
        result = _filter_participants(participants, show_team_members=True)
        assert result is participants  # same list returned unchanged
        assert len(result) == 4

    def test_all_customers_unaffected_by_toggle(self):
        customers = [_MockParticipant(id=i, name=f"C{i}", is_team_member=False) for i in range(5)]
        assert _filter_participants(customers, show_team_members=False) == customers
        assert _filter_participants(customers, show_team_members=True) == customers

    def test_all_team_members_hidden_by_default(self):
        team = [_MockParticipant(id=i, name=f"T{i}", is_team_member=True) for i in range(3)]
        assert _filter_participants(team, show_team_members=False) == []

    def test_empty_list(self):
        assert _filter_participants([], show_team_members=False) == []
        assert _filter_participants([], show_team_members=True) == []

    def test_order_preserved(self):
        participants = self._make_mix()
        result = _filter_participants(participants, show_team_members=False)
        assert result[0].id == 1
        assert result[1].id == 3


# ---------------------------------------------------------------------------
# Participant role assignment (confirm_synthesis is_team_member logic)
# ---------------------------------------------------------------------------

def _is_team_member_from_role(role: str) -> bool:
    """Replica of the role → is_team_member mapping in confirm_synthesis()."""
    return role == "interviewer"


class TestParticipantRoleMapping:
    def test_interviewee_is_not_team_member(self):
        assert _is_team_member_from_role("interviewee") is False

    def test_interviewer_is_team_member(self):
        assert _is_team_member_from_role("interviewer") is True

    def test_unknown_role_is_not_team_member(self):
        # Any unexpected role defaults to customer (not team member)
        for role in ["", "customer", "observer", "guest"]:
            assert _is_team_member_from_role(role) is False


# ---------------------------------------------------------------------------
# Opportunity priority sort key (_opp_sort_key in load_ledger)
# ---------------------------------------------------------------------------

# Fixed reference time so tests are deterministic
_SORT_NOW = datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc)


@dataclass
class _SortableMockOpp:
    id: int
    parent_id: Optional[int] = None
    impact_score: int = 0
    sat_gap_score: int = 0
    date_last_validated: datetime = field(default_factory=lambda: _SORT_NOW)


def _opp_sort_key_fn(o: _SortableMockOpp, evidence_counts: dict, now: datetime) -> tuple:
    """Replica of _opp_sort_key() defined inside load_ledger()."""
    freq = min(evidence_counts.get(o.id, 0), 5)
    priority = o.impact_score + o.sat_gap_score + freq
    db_date = (
        o.date_last_validated.replace(tzinfo=timezone.utc)
        if o.date_last_validated.tzinfo is None
        else o.date_last_validated
    )
    return (-priority, (now - db_date).days)


def _flatten_and_sort(
    opportunities: list,
    evidence_counts: dict | None = None,
    now: datetime | None = None,
) -> list:
    """Replica of the sort + flatten combination from load_ledger()."""
    if evidence_counts is None:
        evidence_counts = {}
    if now is None:
        now = _SORT_NOW

    opp_dict = {o.id: o for o in opportunities}
    opp_children_map: dict = {}
    opp_top_level: list = []

    for opp in opportunities:
        if opp.parent_id and opp.parent_id in opp_dict:
            opp_children_map.setdefault(opp.parent_id, []).append(opp)
        else:
            opp_top_level.append(opp)

    opp_top_level.sort(key=lambda o: _opp_sort_key_fn(o, evidence_counts, now))
    for siblings in opp_children_map.values():
        siblings.sort(key=lambda o: _opp_sort_key_fn(o, evidence_counts, now))

    flat_opps: list = []
    visited_nodes: set = set()

    def _append_children(opp_id: int, level: int) -> None:
        if opp_id in visited_nodes:
            return
        visited_nodes.add(opp_id)
        for child in opp_children_map.get(opp_id, []):
            if child.id not in visited_nodes:
                flat_opps.append((child, level))
                _append_children(child.id, level + 1)

    for opp in opp_top_level:
        if opp.id not in visited_nodes:
            flat_opps.append((opp, 0))
            _append_children(opp.id, 1)

    for opp in opportunities:
        if opp.id not in visited_nodes:
            flat_opps.append((opp, 0))
            _append_children(opp.id, 1)

    return flat_opps


def _make_sortable(id, parent_id=None, impact=0, sat_gap=0, days_old=0):
    return _SortableMockOpp(
        id=id,
        parent_id=parent_id,
        impact_score=impact,
        sat_gap_score=sat_gap,
        date_last_validated=_SORT_NOW - timedelta(days=days_old),
    )


class TestOpportunitySortKey:
    def test_higher_priority_gives_smaller_key(self):
        high = _make_sortable(1, impact=5, sat_gap=5)
        low = _make_sortable(2, impact=0, sat_gap=0)
        assert _opp_sort_key_fn(high, {}, _SORT_NOW) < _opp_sort_key_fn(low, {}, _SORT_NOW)

    def test_tiebreak_fewer_days_old_sorts_first(self):
        """Same priority: 5 days old beats 30 days old."""
        recent = _make_sortable(1, impact=3, days_old=5)
        stale = _make_sortable(2, impact=3, days_old=30)
        assert _opp_sort_key_fn(recent, {}, _SORT_NOW) < _opp_sort_key_fn(stale, {}, _SORT_NOW)

    def test_evidence_included_in_priority_component(self):
        opp = _make_sortable(1)
        key_none = _opp_sort_key_fn(opp, {}, _SORT_NOW)
        key_some = _opp_sort_key_fn(opp, {1: 3}, _SORT_NOW)
        assert key_some < key_none  # more evidence → more negative first element → sorts earlier

    def test_evidence_capped_at_five(self):
        opp = _make_sortable(1)
        assert _opp_sort_key_fn(opp, {1: 5}, _SORT_NOW) == _opp_sort_key_fn(opp, {1: 99}, _SORT_NOW)

    def test_naive_datetime_does_not_raise(self):
        opp = _SortableMockOpp(id=1, date_last_validated=datetime(2026, 2, 10, 12, 0, 0))
        key = _opp_sort_key_fn(opp, {}, _SORT_NOW)
        assert isinstance(key, tuple) and len(key) == 2

    def test_zero_scores_yields_zero_priority(self):
        opp = _make_sortable(1, impact=0, sat_gap=0, days_old=0)
        neg_priority, days = _opp_sort_key_fn(opp, {}, _SORT_NOW)
        assert neg_priority == 0
        assert days == 0

    def test_max_priority_is_minus_fifteen(self):
        opp = _make_sortable(1, impact=5, sat_gap=5)
        neg_priority, _ = _opp_sort_key_fn(opp, {1: 100}, _SORT_NOW)
        assert neg_priority == -15  # -(5 + 5 + min(100, 5))

    def test_days_old_matches_date_difference(self):
        opp = _make_sortable(1, days_old=7)
        _, days = _opp_sort_key_fn(opp, {}, _SORT_NOW)
        assert days == 7

    @pytest.mark.parametrize("impact,sat_gap,evidence,expected_neg_priority", [
        (1, 1, 1, -3),
        (5, 5, 5, -15),
        (3, 0, 0, -3),
        (0, 4, 10, -9),   # evidence capped: 0+4+5=9
        (5, 5, 0, -10),
    ])
    def test_priority_component_parametrized(self, impact, sat_gap, evidence, expected_neg_priority):
        opp = _make_sortable(1, impact=impact, sat_gap=sat_gap)
        neg_priority, _ = _opp_sort_key_fn(opp, {1: evidence}, _SORT_NOW)
        assert neg_priority == expected_neg_priority


class TestOpportunitySortedFlattening:
    def test_top_level_sorted_highest_priority_first(self):
        low = _make_sortable(1, impact=1)
        high = _make_sortable(2, impact=5)
        mid = _make_sortable(3, impact=3)
        result = _flatten_and_sort([low, high, mid])
        ids = [o.id for o, _ in result]
        assert ids == [2, 3, 1]

    def test_tiebreak_by_days_old_ascending(self):
        """Equal priority: more recently mentioned (fewer days old) comes first."""
        older = _make_sortable(1, impact=3, days_old=20)
        newer = _make_sortable(2, impact=3, days_old=5)
        result = _flatten_and_sort([older, newer])
        ids = [o.id for o, _ in result]
        assert ids == [2, 1]  # 5 days old beats 20 days old

    def test_tree_structure_preserved_after_sort(self):
        """A high-priority child still immediately follows its low-priority parent."""
        low_parent = _make_sortable(1, impact=0)
        high_child = _make_sortable(2, parent_id=1, impact=5)
        result = _flatten_and_sort([low_parent, high_child])
        ids = [o.id for o, _ in result]
        # child must follow parent directly, even though child has higher priority
        assert ids.index(2) == ids.index(1) + 1

    def test_siblings_sorted_by_priority(self):
        parent = _make_sortable(1, impact=3)
        weak_child = _make_sortable(2, parent_id=1, impact=0)
        strong_child = _make_sortable(3, parent_id=1, impact=5)
        result = _flatten_and_sort([parent, weak_child, strong_child])
        child_ids = [o.id for o, level in result if level == 1]
        assert child_ids == [3, 2]  # strong before weak among siblings

    def test_evidence_counts_influence_order(self):
        # opp1: impact=3 → priority=3; opp2: impact=0 + 5 evidence → priority=5
        opp1 = _make_sortable(1, impact=3)
        opp2 = _make_sortable(2, impact=0)
        result = _flatten_and_sort([opp1, opp2], evidence_counts={2: 5})
        ids = [o.id for o, _ in result]
        assert ids == [2, 1]

    def test_missing_from_evidence_counts_treated_as_zero(self):
        opp1 = _make_sortable(1, impact=2)
        opp2 = _make_sortable(2, impact=3)
        result = _flatten_and_sort([opp1, opp2], evidence_counts={})
        ids = [o.id for o, _ in result]
        assert ids == [2, 1]

    def test_all_same_priority_sorted_by_days_old_asc(self):
        # ids 3,1,2 — days_old = id*10 (id=1→10d, id=2→20d, id=3→30d)
        opps = [_make_sortable(i, impact=0, days_old=i * 10) for i in [3, 1, 2]]
        result = _flatten_and_sort(opps)
        ids = [o.id for o, _ in result]
        assert ids == [1, 2, 3]

    def test_multilevel_tree_root_order_respected(self):
        """Higher-priority root and its subtree appear before lower-priority root."""
        root_a = _make_sortable(1, impact=5)
        child_a = _make_sortable(2, parent_id=1, impact=1)
        root_b = _make_sortable(3, impact=2)
        child_b = _make_sortable(4, parent_id=3, impact=3)
        result = _flatten_and_sort([root_a, child_a, root_b, child_b])
        ids = [o.id for o, _ in result]
        # root_a (priority=5) comes before root_b (priority=2)
        assert ids.index(1) < ids.index(3)
        # each child immediately follows its own parent
        assert ids.index(2) == ids.index(1) + 1
        assert ids.index(4) == ids.index(3) + 1

    def test_single_opportunity_unchanged(self):
        opp = _make_sortable(1, impact=3, days_old=10)
        result = _flatten_and_sort([opp])
        assert len(result) == 1
        assert result[0] == (opp, 0)

    def test_empty_list_returns_empty(self):
        assert _flatten_and_sort([]) == []


# ---------------------------------------------------------------------------
# Experiment method resolution ("Other" free-text logic from add_experiment)
# ---------------------------------------------------------------------------

_STANDARD_METHODS = {"Prototype Interview", "Fake Door", "A/B Test", "Usability Test", "Survey", "Other"}


def resolve_method(method: str, method_other: str) -> str:
    """Replica of the method-resolution logic in LedgerStateMixin.add_experiment()."""
    if method == "Other":
        return method_other.strip() or "Other"
    return method


class TestExperimentMethodResolution:
    def test_standard_method_returned_directly(self):
        for method in ["Prototype Interview", "Fake Door", "A/B Test", "Usability Test", "Survey"]:
            assert resolve_method(method, "") == method

    def test_other_with_free_text_returns_free_text(self):
        assert resolve_method("Other", "Dogfooding") == "Dogfooding"

    def test_other_with_empty_free_text_returns_other(self):
        assert resolve_method("Other", "") == "Other"

    def test_other_with_whitespace_only_returns_other(self):
        assert resolve_method("Other", "   ") == "Other"

    def test_other_with_padded_free_text_strips_whitespace(self):
        assert resolve_method("Other", "  Field Study  ") == "Field Study"


# ---------------------------------------------------------------------------
# Synthesis theme formatting (prompt preparation in run_synthesis)
# ---------------------------------------------------------------------------


def format_existing_themes(themes_dict: dict) -> str:
    """Replica of the theme-list formatting used when building the synthesis prompt."""
    themes = sorted(set(themes_dict.values())) if themes_dict else []
    return ", ".join(themes) if themes else "None yet — create new themes as needed."


class TestSynthesisThemeFormatting:
    def test_empty_dict_returns_fallback(self):
        result = format_existing_themes({})
        assert result == "None yet — create new themes as needed."

    def test_single_theme_returned(self):
        result = format_existing_themes({1: "Onboarding"})
        assert result == "Onboarding"

    def test_multiple_themes_sorted_and_comma_separated(self):
        result = format_existing_themes({1: "Billing", 2: "Onboarding", 3: "Performance"})
        assert result == "Billing, Onboarding, Performance"

    def test_duplicate_themes_deduplicated(self):
        # Two opportunities share the same theme — only one copy should appear.
        result = format_existing_themes({1: "Billing", 2: "Billing", 3: "Onboarding"})
        assert result == "Billing, Onboarding"

    def test_themes_are_sorted_alphabetically(self):
        result = format_existing_themes({1: "Zebra", 2: "Alpha", 3: "Mango"})
        assert result == "Alpha, Mango, Zebra"


# ---------------------------------------------------------------------------
# Theme inheritance (confirm_synthesis opportunity matching logic)
# ---------------------------------------------------------------------------


def resolve_theme(matched_id, existing_themes: dict, synthesized_theme: str) -> str:
    """
    Replica of the theme-resolution logic in confirm_synthesis():
    inherit the existing theme when a duplicate is matched; otherwise
    use the LLM-synthesized theme (or fall back to "General").
    """
    theme = existing_themes.get(matched_id) if matched_id else None
    if not theme:
        theme = synthesized_theme or "General"
    return theme


class TestThemeInheritance:
    def test_no_match_uses_synthesized_theme(self):
        result = resolve_theme(None, {1: "Billing"}, "Onboarding")
        assert result == "Onboarding"

    def test_match_found_inherits_existing_theme(self):
        result = resolve_theme(1, {1: "Billing"}, "Onboarding")
        assert result == "Billing"

    def test_match_found_but_theme_empty_falls_back_to_synthesized(self):
        result = resolve_theme(1, {1: ""}, "Performance")
        assert result == "Performance"

    def test_no_match_and_no_synthesized_theme_returns_general(self):
        result = resolve_theme(None, {}, "")
        assert result == "General"

    def test_match_found_synthesized_theme_ignored(self):
        # Even if the LLM synthesized a different theme, the matched opp's
        # existing theme takes precedence.
        result = resolve_theme(42, {42: "Workflow"}, "Onboarding")
        assert result == "Workflow"

    def test_no_match_with_none_themes_dict_key_missing(self):
        # matched_id present but not in the dict → falls back to synthesized
        result = resolve_theme(99, {1: "Billing"}, "Search")
        assert result == "Search"
