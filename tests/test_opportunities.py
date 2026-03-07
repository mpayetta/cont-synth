"""Unit tests for opportunity management business logic.

Covers:
- View-building functions: theme groups, kanban, matrix (5×5)
- Opportunity filter logic (by theme, persona, priority, search text)
- is_target exclusive toggle logic
- Opportunity scoring (impact_score, sat_gap_score, priority_score)
- DB-backed CRUD for opportunities and scoring fields
- Opportunity merge logic
"""
import pytest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import select

from cont_synth.state.core import (
    BoardColumn,
    LedgerItem,
    MatrixCell,
    OutcomeItem,
    PersonaBadge,
    QuoteItem,
    SolutionItem,
    ThemeGroup,
)


# ---------------------------------------------------------------------------
# Helpers: build LedgerItem fixtures
# ---------------------------------------------------------------------------

def _make_ledger_item(
    opp_id: int,
    theme: str = "General",
    opportunity: str = "Need something",
    personas: list | None = None,
    evidence_count: int = 0,
    impact_score: int = 0,
    sat_gap_score: int = 0,
    priority_score: int = 0,
    parent_id: int = -1,
    indent_level: int = 0,
    status: str = "FRESH",
    is_cross_functional: bool = False,
    running_experiments: int = 0,
) -> LedgerItem:
    badges = personas or []
    evidence = [
        QuoteItem(interview_id=i, persona_name="User", persona_color="blue", text=f"Quote {i}")
        for i in range(evidence_count)
    ]
    return LedgerItem(
        opportunity_id=opp_id,
        parent_id=parent_id,
        indent_level=indent_level,
        theme=theme,
        personas_affected=badges,
        opportunity=opportunity,
        status=status,
        status_color="green",
        days_old=5,
        is_cross_functional=is_cross_functional,
        evidence=evidence,
        impact_score=impact_score,
        sat_gap_score=sat_gap_score,
        priority_score=priority_score,
        running_experiments=running_experiments,
    )


# ---------------------------------------------------------------------------
# Theme group view building
# ---------------------------------------------------------------------------

def _build_theme_groups(items: list[LedgerItem]) -> list[ThemeGroup]:
    """Replica of get_ledger_as_theme_groups() in LedgerStateMixin."""
    groups: dict[str, list[LedgerItem]] = {}
    for item in items:
        groups.setdefault(item.theme, []).append(item)

    result = []
    for theme, opps in sorted(groups.items()):
        count = len(opps)
        avg_priority = sum(o.priority_score for o in opps) // count if count else 0
        result.append(ThemeGroup(theme=theme, count=count, avg_priority=avg_priority, opps=opps))
    return result


class TestThemeGroupView:
    def test_empty_items_returns_no_groups(self):
        assert _build_theme_groups([]) == []

    def test_single_theme_group(self):
        items = [_make_ledger_item(1, theme="Billing"), _make_ledger_item(2, theme="Billing")]
        groups = _build_theme_groups(items)
        assert len(groups) == 1
        assert groups[0].theme == "Billing"
        assert groups[0].count == 2

    def test_multiple_themes_creates_multiple_groups(self):
        items = [
            _make_ledger_item(1, theme="Billing"),
            _make_ledger_item(2, theme="Workflow"),
            _make_ledger_item(3, theme="Billing"),
            _make_ledger_item(4, theme="Onboarding"),
        ]
        groups = _build_theme_groups(items)
        assert len(groups) == 3
        themes = {g.theme for g in groups}
        assert themes == {"Billing", "Workflow", "Onboarding"}

    def test_theme_groups_sorted_alphabetically(self):
        items = [
            _make_ledger_item(1, theme="Zebra"),
            _make_ledger_item(2, theme="Alpha"),
            _make_ledger_item(3, theme="Mango"),
        ]
        groups = _build_theme_groups(items)
        assert [g.theme for g in groups] == ["Alpha", "Mango", "Zebra"]

    def test_count_matches_items_in_group(self):
        items = [_make_ledger_item(i, theme="Same") for i in range(7)]
        groups = _build_theme_groups(items)
        assert groups[0].count == 7

    def test_avg_priority_computed(self):
        items = [
            _make_ledger_item(1, theme="T", priority_score=10),
            _make_ledger_item(2, theme="T", priority_score=6),
        ]
        groups = _build_theme_groups(items)
        assert groups[0].avg_priority == 8


# ---------------------------------------------------------------------------
# Kanban view building (by priority tiers)
# ---------------------------------------------------------------------------

def _priority_tier(priority_score: int) -> str:
    """Assign a kanban column based on priority score."""
    if priority_score >= 10:
        return "High"
    elif priority_score >= 6:
        return "Medium"
    elif priority_score >= 1:
        return "Low"
    return "Unrated"


def _build_kanban(items: list[LedgerItem]) -> list[BoardColumn]:
    """Replica of get_ledger_as_kanban() in LedgerStateMixin."""
    cols: dict[str, list[LedgerItem]] = {"High": [], "Medium": [], "Low": [], "Unrated": []}
    colors = {"High": "green", "Medium": "yellow", "Low": "orange", "Unrated": "gray"}
    for item in items:
        tier = _priority_tier(item.priority_score)
        cols[tier].append(item)
    return [
        BoardColumn(label=label, color=colors[label], opps=opps)
        for label, opps in cols.items()
    ]


class TestKanbanView:
    def test_empty_items_creates_four_empty_columns(self):
        cols = _build_kanban([])
        assert len(cols) == 4
        assert all(len(c.opps) == 0 for c in cols)

    def test_high_priority_item_in_high_column(self):
        items = [_make_ledger_item(1, priority_score=12)]
        cols = _build_kanban(items)
        high_col = next(c for c in cols if c.label == "High")
        assert len(high_col.opps) == 1

    def test_unrated_item_in_unrated_column(self):
        items = [_make_ledger_item(1, priority_score=0)]
        cols = _build_kanban(items)
        unrated_col = next(c for c in cols if c.label == "Unrated")
        assert len(unrated_col.opps) == 1

    def test_priority_boundaries(self):
        assert _priority_tier(0) == "Unrated"
        assert _priority_tier(1) == "Low"
        assert _priority_tier(5) == "Low"
        assert _priority_tier(6) == "Medium"
        assert _priority_tier(9) == "Medium"
        assert _priority_tier(10) == "High"
        assert _priority_tier(15) == "High"

    def test_all_four_columns_exist(self):
        cols = _build_kanban([])
        labels = {c.label for c in cols}
        assert labels == {"High", "Medium", "Low", "Unrated"}

    def test_mixed_priorities_distributed_correctly(self):
        items = [
            _make_ledger_item(1, priority_score=0),
            _make_ledger_item(2, priority_score=3),
            _make_ledger_item(3, priority_score=7),
            _make_ledger_item(4, priority_score=12),
        ]
        cols = _build_kanban(items)
        col_map = {c.label: len(c.opps) for c in cols}
        assert col_map["Unrated"] == 1
        assert col_map["Low"] == 1
        assert col_map["Medium"] == 1
        assert col_map["High"] == 1


# ---------------------------------------------------------------------------
# Matrix view building (5×5 Impact × Sat-Gap)
# ---------------------------------------------------------------------------

def _build_matrix(items: list[LedgerItem]) -> list[MatrixCell]:
    """Replica of get_ledger_as_matrix() in LedgerStateMixin."""
    cells: dict[tuple[int, int], list[LedgerItem]] = {}
    for sg in range(1, 6):
        for imp in range(1, 6):
            cells[(sg, imp)] = []

    for item in items:
        if item.impact_score > 0 and item.sat_gap_score > 0:
            key = (item.sat_gap_score, item.impact_score)
            if key in cells:
                cells[key].append(item)

    result = []
    for sg in range(1, 6):
        for imp in range(1, 6):
            is_sweet_spot = sg >= 3 and imp >= 3
            result.append(MatrixCell(
                sat_gap=sg,
                impact=imp,
                opps=cells[(sg, imp)],
                is_sweet_spot=is_sweet_spot,
            ))
    return result


class TestMatrixView:
    def test_matrix_has_25_cells(self):
        cells = _build_matrix([])
        assert len(cells) == 25

    def test_empty_items_all_cells_empty(self):
        cells = _build_matrix([])
        assert all(len(c.opps) == 0 for c in cells)

    def test_scored_item_placed_in_correct_cell(self):
        items = [_make_ledger_item(1, impact_score=4, sat_gap_score=3)]
        cells = _build_matrix(items)
        matching = [c for c in cells if c.sat_gap == 3 and c.impact == 4]
        assert len(matching) == 1
        assert len(matching[0].opps) == 1

    def test_unscored_item_not_in_any_cell(self):
        items = [_make_ledger_item(1, impact_score=0, sat_gap_score=0)]
        cells = _build_matrix(items)
        assert all(len(c.opps) == 0 for c in cells)

    def test_sweet_spot_cells_are_top_right(self):
        cells = _build_matrix([])
        sweet_cells = [c for c in cells if c.is_sweet_spot]
        assert len(sweet_cells) == 9
        for c in sweet_cells:
            assert c.sat_gap >= 3
            assert c.impact >= 3

    def test_non_sweet_spot_cells(self):
        cells = _build_matrix([])
        not_sweet = [c for c in cells if not c.is_sweet_spot]
        assert len(not_sweet) == 16

    def test_multiple_items_same_cell(self):
        items = [
            _make_ledger_item(1, impact_score=5, sat_gap_score=5),
            _make_ledger_item(2, impact_score=5, sat_gap_score=5),
        ]
        cells = _build_matrix(items)
        cell_5_5 = next(c for c in cells if c.sat_gap == 5 and c.impact == 5)
        assert len(cell_5_5.opps) == 2


# ---------------------------------------------------------------------------
# Opportunity filter logic
# ---------------------------------------------------------------------------

def _filter_by_theme(items: list[LedgerItem], selected_themes: set[str]) -> list[LedgerItem]:
    if not selected_themes:
        return items
    return [i for i in items if i.theme in selected_themes]


def _filter_by_search(items: list[LedgerItem], search_text: str) -> list[LedgerItem]:
    if not search_text.strip():
        return items
    q = search_text.lower()
    return [i for i in items if q in i.opportunity.lower() or q in i.theme.lower()]


def _filter_by_priority(items: list[LedgerItem], min_priority: int) -> list[LedgerItem]:
    if min_priority == 0:
        return items
    return [i for i in items if i.priority_score >= min_priority]


class TestOpportunityFilters:
    def _make_items(self):
        return [
            _make_ledger_item(1, theme="Billing", opportunity="Can't export invoices", priority_score=12),
            _make_ledger_item(2, theme="Workflow", opportunity="Batch actions are slow", priority_score=6),
            _make_ledger_item(3, theme="Billing", opportunity="Payment methods limited", priority_score=3),
            _make_ledger_item(4, theme="Onboarding", opportunity="Setup takes too long", priority_score=0),
        ]

    def test_no_theme_filter_returns_all(self):
        items = self._make_items()
        assert _filter_by_theme(items, set()) == items

    def test_theme_filter_single_theme(self):
        items = self._make_items()
        result = _filter_by_theme(items, {"Billing"})
        assert len(result) == 2
        assert all(i.theme == "Billing" for i in result)

    def test_theme_filter_multiple_themes(self):
        items = self._make_items()
        result = _filter_by_theme(items, {"Billing", "Workflow"})
        assert len(result) == 3

    def test_theme_filter_nonexistent_theme(self):
        items = self._make_items()
        result = _filter_by_theme(items, {"Nonexistent"})
        assert result == []

    def test_search_filter_empty_returns_all(self):
        items = self._make_items()
        assert _filter_by_search(items, "") == items

    def test_search_filter_case_insensitive(self):
        items = self._make_items()
        result = _filter_by_search(items, "INVOICE")
        assert len(result) == 1
        assert result[0].opportunity_id == 1

    def test_search_filter_partial_match(self):
        items = self._make_items()
        result = _filter_by_search(items, "batch")
        assert len(result) == 1

    def test_search_filter_matches_theme(self):
        items = self._make_items()
        result = _filter_by_search(items, "billing")
        assert len(result) == 2

    def test_priority_filter_zero_returns_all(self):
        items = self._make_items()
        assert _filter_by_priority(items, 0) == items

    def test_priority_filter_removes_low_priority(self):
        items = self._make_items()
        result = _filter_by_priority(items, 6)
        assert len(result) == 2
        assert all(i.priority_score >= 6 for i in result)

    def test_priority_filter_removes_unrated(self):
        items = self._make_items()
        result = _filter_by_priority(items, 1)
        # excludes opp 4 (priority_score=0)
        assert all(i.priority_score >= 1 for i in result)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# is_target exclusive toggle logic
# ---------------------------------------------------------------------------

@dataclass
class _MockOppRow:
    id: int
    is_target: bool = False


def _toggle_target(opps: list[_MockOppRow], target_id: int) -> list[_MockOppRow]:
    """Replica of set_target_opportunity() exclusive toggle."""
    currently_target = next((o for o in opps if o.id == target_id), None)
    if currently_target is None:
        return opps
    new_target_state = not currently_target.is_target
    return [
        _MockOppRow(id=o.id, is_target=(new_target_state and o.id == target_id))
        for o in opps
    ]


class TestIsTargetToggle:
    def test_toggle_sets_one_target(self):
        opps = [_MockOppRow(id=1), _MockOppRow(id=2), _MockOppRow(id=3)]
        result = _toggle_target(opps, 2)
        assert result[1].is_target is True
        assert result[0].is_target is False
        assert result[2].is_target is False

    def test_toggle_clears_previous_target(self):
        opps = [_MockOppRow(id=1, is_target=True), _MockOppRow(id=2)]
        result = _toggle_target(opps, 2)
        assert result[0].is_target is False
        assert result[1].is_target is True

    def test_toggle_current_target_clears_it(self):
        opps = [_MockOppRow(id=1, is_target=True)]
        result = _toggle_target(opps, 1)
        assert result[0].is_target is False

    def test_only_one_target_at_a_time(self):
        opps = [_MockOppRow(id=i) for i in range(5)]
        result = _toggle_target(opps, 3)
        targets = [o for o in result if o.is_target]
        assert len(targets) == 1
        assert targets[0].id == 3


# ---------------------------------------------------------------------------
# Opportunity scoring DB tests
# ---------------------------------------------------------------------------

class TestOpportunityScoringDB:
    def test_impact_score_stored(self, db_session):
        from cont_synth.models import Opportunity, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        opp = Opportunity(product_id=product.id, statement="Need fast search", impact_score=4)
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        assert opp.impact_score == 4

    def test_sat_gap_score_stored(self, db_session):
        from cont_synth.models import Opportunity, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        opp = Opportunity(product_id=product.id, statement="Need better onboarding", sat_gap_score=3)
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        assert opp.sat_gap_score == 3

    def test_score_defaults_to_zero(self, db_session):
        from cont_synth.models import Opportunity, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        opp = Opportunity(product_id=product.id, statement="Unrated need")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        assert opp.impact_score == 0
        assert opp.sat_gap_score == 0

    def test_score_update_persisted(self, db_session):
        from cont_synth.models import Opportunity, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        opp = Opportunity(product_id=product.id, statement="Need X")
        db_session.add(opp)
        db_session.commit()
        db_session.refresh(opp)

        opp.impact_score = 5
        opp.sat_gap_score = 4
        db_session.add(opp)
        db_session.commit()

        reloaded = db_session.get(Opportunity, opp.id)
        assert reloaded.impact_score == 5
        assert reloaded.sat_gap_score == 4

    def test_all_score_values_1_to_5(self, db_session):
        from cont_synth.models import Opportunity, Product

        product = Product(name="WS")
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        for score in range(1, 6):
            opp = Opportunity(product_id=product.id, statement=f"Opp {score}", impact_score=score)
            db_session.add(opp)
        db_session.commit()

        opps = db_session.exec(select(Opportunity)).all()
        scores = {o.impact_score for o in opps}
        assert scores == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# Opportunity merge logic
# ---------------------------------------------------------------------------

@dataclass
class _MergeOpp:
    id: int
    statement: str
    theme: str


def _merge_opportunities(
    keep: _MergeOpp,
    discard: _MergeOpp,
    all_opps: list[_MergeOpp],
) -> tuple[list[_MergeOpp], list[int]]:
    """
    Replica of merge_opportunities logic:
    - Keep the 'keep' opp with its statement+theme
    - Discard the other opp
    - Return updated list and list of moved IDs
    """
    updated = [o for o in all_opps if o.id != discard.id]
    moved_ids = [discard.id]
    return updated, moved_ids


class TestOpportunityMerge:
    def test_merge_removes_discarded_opp(self):
        opps = [_MergeOpp(1, "Need A", "Billing"), _MergeOpp(2, "Need B", "Billing")]
        result, moved = _merge_opportunities(opps[0], opps[1], opps)
        assert len(result) == 1
        assert result[0].id == 1

    def test_merged_id_returned(self):
        opps = [_MergeOpp(1, "Keep", "T"), _MergeOpp(2, "Discard", "T")]
        _, moved = _merge_opportunities(opps[0], opps[1], opps)
        assert 2 in moved

    def test_kept_opp_retains_statement_and_theme(self):
        keep = _MergeOpp(1, "Keep This Statement", "Billing")
        discard = _MergeOpp(2, "Discard This", "Other Theme")
        opps = [keep, discard]
        result, _ = _merge_opportunities(keep, discard, opps)
        assert result[0].statement == "Keep This Statement"
        assert result[0].theme == "Billing"

    def test_empty_list_after_merge_of_two(self):
        opps = [_MergeOpp(1, "A", "T"), _MergeOpp(2, "B", "T")]
        result, _ = _merge_opportunities(opps[0], opps[1], opps)
        # Started with 2, removed 1
        assert len(result) == 1

    def test_merge_with_three_opps_keeps_two(self):
        opps = [_MergeOpp(1, "A", "T"), _MergeOpp(2, "B", "T"), _MergeOpp(3, "C", "T")]
        result, _ = _merge_opportunities(opps[0], opps[1], opps)
        assert len(result) == 2
        ids = {o.id for o in result}
        assert 2 not in ids
