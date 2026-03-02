"""Unit tests for the home dashboard business logic in load_dashboard().

All logic is replicated as pure Python — no Reflex runtime, no database.
Each helper mirrors a specific computation from NavigationStateMixin.load_dashboard().
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pytest


# ---------------------------------------------------------------------------
# Shared helpers / mock types
# ---------------------------------------------------------------------------

@dataclass
class _MockInterview:
    """Minimal interview row for testing date/bucketing logic."""
    id: int
    interview_date: Optional[str] = None     # ISO string or None
    date_logged: Optional[datetime] = None   # UTC datetime


def _make_interview(
    id: int,
    interview_date: Optional[str] = None,
    days_ago_logged: int = 0,
) -> _MockInterview:
    logged = datetime.now(timezone.utc) - timedelta(days=days_ago_logged)
    return _MockInterview(id=id, interview_date=interview_date, date_logged=logged)


# ---------------------------------------------------------------------------
# _eff_date — effective date helper
# Prefers interview_date (ISO), falls back to date_logged.date()
# ---------------------------------------------------------------------------

def _eff_date(inv: _MockInterview) -> Optional[date]:
    """Replica of the inner _eff_date() function inside load_dashboard()."""
    if inv.interview_date:
        try:
            return date.fromisoformat(inv.interview_date)
        except (ValueError, TypeError):
            pass
    return inv.date_logged.date() if inv.date_logged else None


class TestEffDate:
    def test_prefers_interview_date_when_set(self):
        inv = _make_interview(1, interview_date="2026-01-15", days_ago_logged=5)
        result = _eff_date(inv)
        assert result == date(2026, 1, 15)

    def test_falls_back_to_date_logged_when_no_interview_date(self):
        today = date.today()
        inv = _make_interview(1, interview_date=None, days_ago_logged=3)
        result = _eff_date(inv)
        assert result == today - timedelta(days=3)

    def test_falls_back_to_date_logged_on_invalid_interview_date(self):
        today = date.today()
        inv = _make_interview(1, interview_date="not-a-date", days_ago_logged=2)
        result = _eff_date(inv)
        assert result == today - timedelta(days=2)

    def test_returns_none_when_both_missing(self):
        inv = _MockInterview(id=1, interview_date=None, date_logged=None)
        assert _eff_date(inv) is None

    def test_interview_date_takes_precedence_over_recent_date_logged(self):
        # interview_date is 30 days ago; date_logged is today — should use interview_date
        old_date = (date.today() - timedelta(days=30)).isoformat()
        inv = _make_interview(1, interview_date=old_date, days_ago_logged=0)
        result = _eff_date(inv)
        assert result == date.today() - timedelta(days=30)

    @pytest.mark.parametrize("bad_date", ["", "2026-13-01", "01/15/2026", "yesterday"])
    def test_invalid_interview_date_formats_fall_back(self, bad_date):
        inv = _make_interview(1, interview_date=bad_date, days_ago_logged=0)
        result = _eff_date(inv)
        # Falls back to date_logged, which is today
        assert result == date.today()


# ---------------------------------------------------------------------------
# Days since last interview
# ---------------------------------------------------------------------------

def _days_since_last(interviews: list[_MockInterview], today: date) -> int:
    """Replica of the days-since-last computation in load_dashboard()."""
    max_idate: Optional[date] = None
    for inv in interviews:
        d = _eff_date(inv)
        if d and (max_idate is None or d > max_idate):
            max_idate = d
    return (today - max_idate).days if max_idate else -1


class TestDaysSinceLast:
    def test_no_interviews_returns_minus_one(self):
        assert _days_since_last([], date.today()) == -1

    def test_interview_today(self):
        inv = _make_interview(1, interview_date=date.today().isoformat())
        assert _days_since_last([inv], date.today()) == 0

    def test_interview_yesterday(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        inv = _make_interview(1, interview_date=yesterday)
        assert _days_since_last([inv], date.today()) == 1

    def test_takes_most_recent_across_multiple(self):
        today = date.today()
        interviews = [
            _make_interview(1, interview_date=(today - timedelta(days=10)).isoformat()),
            _make_interview(2, interview_date=(today - timedelta(days=3)).isoformat()),
            _make_interview(3, interview_date=(today - timedelta(days=20)).isoformat()),
        ]
        assert _days_since_last(interviews, today) == 3

    def test_not_fooled_by_insertion_order(self):
        """Most recent interview can appear anywhere in the list."""
        today = date.today()
        interviews = [
            _make_interview(1, interview_date=(today - timedelta(days=15)).isoformat()),
            _make_interview(2, interview_date=(today - timedelta(days=2)).isoformat()),
            _make_interview(3, interview_date=(today - timedelta(days=8)).isoformat()),
        ]
        assert _days_since_last(interviews, today) == 2

    def test_uses_date_logged_fallback(self):
        today = date.today()
        # No interview_date set; date_logged was 5 days ago
        inv = _make_interview(1, interview_date=None, days_ago_logged=5)
        assert _days_since_last([inv], today) == 5

    def test_interview_with_none_date_skipped(self):
        today = date.today()
        good = _make_interview(1, interview_date=(today - timedelta(days=4)).isoformat())
        bad = _MockInterview(id=2, interview_date=None, date_logged=None)
        assert _days_since_last([good, bad], today) == 4

    def test_old_interview_shows_large_days(self):
        sixty_days_ago = (date.today() - timedelta(days=60)).isoformat()
        inv = _make_interview(1, interview_date=sixty_days_ago)
        assert _days_since_last([inv], date.today()) == 60

    def test_cadence_color_thresholds(self):
        """Validate the <7 / 7-14 / >14 colour bands used in the UI."""
        today = date.today()
        def days(n): return _days_since_last(
            [_make_interview(1, interview_date=(today - timedelta(days=n)).isoformat())], today
        )
        assert days(0) < 7   # green
        assert days(6) < 7   # green boundary
        assert days(7) >= 7  # amber starts
        assert days(14) <= 14  # amber boundary
        assert days(15) > 14   # red starts


# ---------------------------------------------------------------------------
# Weekly interview bucketing
# ---------------------------------------------------------------------------

def _bucket_interviews(interviews: list[_MockInterview], today: date) -> list[int]:
    """Replica of the weekly_counts computation in load_dashboard().

    Returns a list of 8 ints where index 0 = current week, index 7 = 7 weeks ago.
    """
    weekly_counts = [0] * 8
    for inv in interviews:
        d = _eff_date(inv)
        if d:
            days_ago = (today - d).days
            if 0 <= days_ago <= 55:
                week_idx = days_ago // 7
                if week_idx < 8:
                    weekly_counts[week_idx] += 1
    return weekly_counts


class TestWeeklyBuckets:
    def test_empty_interviews(self):
        counts = _bucket_interviews([], date.today())
        assert counts == [0] * 8

    def test_interview_today_lands_in_week_zero(self):
        today = date.today()
        inv = _make_interview(1, interview_date=today.isoformat())
        counts = _bucket_interviews([inv], today)
        assert counts[0] == 1
        assert sum(counts[1:]) == 0

    def test_six_days_ago_in_week_zero(self):
        today = date.today()
        inv = _make_interview(1, interview_date=(today - timedelta(days=6)).isoformat())
        counts = _bucket_interviews([inv], today)
        assert counts[0] == 1

    def test_seven_days_ago_in_week_one(self):
        today = date.today()
        inv = _make_interview(1, interview_date=(today - timedelta(days=7)).isoformat())
        counts = _bucket_interviews([inv], today)
        assert counts[0] == 0
        assert counts[1] == 1

    def test_55_days_ago_in_week_seven(self):
        today = date.today()
        inv = _make_interview(1, interview_date=(today - timedelta(days=55)).isoformat())
        counts = _bucket_interviews([inv], today)
        assert counts[7] == 1

    def test_56_days_ago_excluded(self):
        today = date.today()
        inv = _make_interview(1, interview_date=(today - timedelta(days=56)).isoformat())
        counts = _bucket_interviews([inv], today)
        assert sum(counts) == 0

    def test_future_interview_excluded(self):
        today = date.today()
        inv = _make_interview(1, interview_date=(today + timedelta(days=1)).isoformat())
        counts = _bucket_interviews([inv], today)
        assert sum(counts) == 0

    def test_multiple_interviews_same_week_accumulate(self):
        today = date.today()
        interviews = [
            _make_interview(i, interview_date=(today - timedelta(days=i)).isoformat())
            for i in range(6)  # all within week 0 (0–6 days ago)
        ]
        counts = _bucket_interviews(interviews, today)
        assert counts[0] == 6

    def test_interviews_spread_across_weeks(self):
        today = date.today()
        interviews = [
            _make_interview(1, interview_date=(today - timedelta(days=0)).isoformat()),   # wk 0
            _make_interview(2, interview_date=(today - timedelta(days=10)).isoformat()),  # wk 1
            _make_interview(3, interview_date=(today - timedelta(days=21)).isoformat()),  # wk 3
        ]
        counts = _bucket_interviews(interviews, today)
        assert counts[0] == 1
        assert counts[1] == 1
        assert counts[3] == 1
        assert sum(counts) == 3

    def test_always_returns_8_buckets(self):
        counts = _bucket_interviews([], date.today())
        assert len(counts) == 8


# ---------------------------------------------------------------------------
# Bar height normalisation
# ---------------------------------------------------------------------------

MAX_BAR_HEIGHT = 48


def _compute_bars(weekly_counts: list[int], today: date) -> list[dict]:
    """Replica of the bar-generation loop in load_dashboard()."""
    max_count = max(weekly_counts) if any(weekly_counts) else 1
    bars = []
    for i in range(7, -1, -1):  # oldest → newest
        week_start = today - timedelta(days=i * 7 + 6)
        cnt = weekly_counts[i]
        h = int(cnt * MAX_BAR_HEIGHT / max_count) if cnt > 0 else 0
        bars.append({
            "week_label": week_start.strftime("%b %d"),
            "count": cnt,
            "height_css": f"{h}px",
        })
    return bars


class TestBarHeights:
    def test_always_produces_eight_bars(self):
        counts = [0] * 8
        bars = _compute_bars(counts, date.today())
        assert len(bars) == 8

    def test_zero_counts_all_zero_height(self):
        bars = _compute_bars([0] * 8, date.today())
        assert all(b["height_css"] == "0px" for b in bars)
        assert all(b["count"] == 0 for b in bars)

    def test_max_count_week_gets_full_height(self):
        counts = [0, 0, 0, 0, 0, 0, 0, 3]  # index 7 has max (3)
        bars = _compute_bars(counts, date.today())
        # index 7 = oldest week; bars[0] is oldest → bars[0] should be 48px
        assert bars[0]["height_css"] == f"{MAX_BAR_HEIGHT}px"

    def test_lower_counts_proportional(self):
        counts = [0] * 8
        counts[0] = 2  # current week: 2 (max)
        counts[1] = 1  # last week: 1 (half of max)
        bars = _compute_bars(counts, date.today())
        # bars[-1] is current week (index 0), bars[-2] is last week (index 1)
        current_h = int(2 * MAX_BAR_HEIGHT / 2)  # = 48
        last_h = int(1 * MAX_BAR_HEIGHT / 2)     # = 24
        assert bars[-1]["height_css"] == f"{current_h}px"
        assert bars[-2]["height_css"] == f"{last_h}px"

    def test_single_interview_gets_full_height(self):
        counts = [0] * 7 + [1]  # week 7 has 1 interview
        bars = _compute_bars(counts, date.today())
        assert bars[0]["height_css"] == f"{MAX_BAR_HEIGHT}px"

    def test_bars_ordered_oldest_to_newest(self):
        """bars[0] is 7 weeks ago, bars[7] is current week."""
        today = date.today()
        bars = _compute_bars([0] * 8, today)
        # bars[0] week_start = today - 7*7+6 = today - 55 days
        expected_oldest = (today - timedelta(days=55)).strftime("%b %d")
        assert bars[0]["week_label"] == expected_oldest

    def test_current_week_is_last_bar(self):
        today = date.today()
        bars = _compute_bars([0] * 8, today)
        expected_label = (today - timedelta(days=6)).strftime("%b %d")
        assert bars[7]["week_label"] == expected_label

    def test_height_css_format(self):
        counts = [1, 2, 0, 3, 0, 1, 2, 1]
        bars = _compute_bars(counts, date.today())
        for bar in bars:
            assert bar["height_css"].endswith("px")
            px_val = int(bar["height_css"][:-2])
            assert 0 <= px_val <= MAX_BAR_HEIGHT


# ---------------------------------------------------------------------------
# Experiment pipeline aggregation
# ---------------------------------------------------------------------------

@dataclass
class _MockExperiment:
    id: int
    status: str   # "Draft" | "Running" | "Concluded"
    signal: str   # "Pending" | "Validated" | "Invalidated"


def _aggregate_experiments(experiments: list[_MockExperiment]) -> dict:
    """Replica of the experiment count logic in load_dashboard()."""
    concluded = [e for e in experiments if e.status == "Concluded"]
    return {
        "draft":       sum(1 for e in experiments if e.status == "Draft"),
        "running":     sum(1 for e in experiments if e.status == "Running"),
        "concluded":   len(concluded),
        "validated":   sum(1 for e in concluded if e.signal == "Validated"),
        "invalidated": sum(1 for e in concluded if e.signal == "Invalidated"),
    }


class TestExperimentAggregation:
    def test_empty_list(self):
        result = _aggregate_experiments([])
        assert result == {"draft": 0, "running": 0, "concluded": 0, "validated": 0, "invalidated": 0}

    def test_counts_draft(self):
        exps = [_MockExperiment(i, "Draft", "Pending") for i in range(3)]
        result = _aggregate_experiments(exps)
        assert result["draft"] == 3
        assert result["running"] == 0
        assert result["concluded"] == 0

    def test_counts_running(self):
        exps = [_MockExperiment(i, "Running", "Pending") for i in range(2)]
        result = _aggregate_experiments(exps)
        assert result["running"] == 2

    def test_counts_concluded(self):
        exps = [
            _MockExperiment(1, "Concluded", "Validated"),
            _MockExperiment(2, "Concluded", "Invalidated"),
            _MockExperiment(3, "Concluded", "Pending"),
        ]
        result = _aggregate_experiments(exps)
        assert result["concluded"] == 3

    def test_validated_only_from_concluded(self):
        exps = [
            _MockExperiment(1, "Draft", "Validated"),      # shouldn't count
            _MockExperiment(2, "Concluded", "Validated"),  # should count
            _MockExperiment(3, "Running", "Validated"),    # shouldn't count
        ]
        result = _aggregate_experiments(exps)
        assert result["validated"] == 1

    def test_invalidated_only_from_concluded(self):
        exps = [
            _MockExperiment(1, "Concluded", "Invalidated"),
            _MockExperiment(2, "Concluded", "Validated"),
            _MockExperiment(3, "Running", "Invalidated"),  # shouldn't count
        ]
        result = _aggregate_experiments(exps)
        assert result["invalidated"] == 1
        assert result["validated"] == 1

    def test_pending_concluded_not_in_validated_or_invalidated(self):
        exps = [_MockExperiment(1, "Concluded", "Pending")]
        result = _aggregate_experiments(exps)
        assert result["concluded"] == 1
        assert result["validated"] == 0
        assert result["invalidated"] == 0

    def test_mixed_pipeline(self):
        exps = [
            _MockExperiment(1, "Draft", "Pending"),
            _MockExperiment(2, "Draft", "Pending"),
            _MockExperiment(3, "Running", "Pending"),
            _MockExperiment(4, "Concluded", "Validated"),
            _MockExperiment(5, "Concluded", "Invalidated"),
            _MockExperiment(6, "Concluded", "Pending"),
        ]
        result = _aggregate_experiments(exps)
        assert result["draft"] == 2
        assert result["running"] == 1
        assert result["concluded"] == 3
        assert result["validated"] == 1
        assert result["invalidated"] == 1

    def test_totals_add_up(self):
        exps = [
            _MockExperiment(1, "Draft", "Pending"),
            _MockExperiment(2, "Running", "Pending"),
            _MockExperiment(3, "Concluded", "Validated"),
        ]
        result = _aggregate_experiments(exps)
        assert result["draft"] + result["running"] + result["concluded"] == len(exps)


# ---------------------------------------------------------------------------
# Opportunity health counts
# ---------------------------------------------------------------------------

@dataclass
class _MockLink:
    opportunity_id: int


@dataclass
class _MockSolution:
    id: int
    opportunity_id: int
    status: str


def _opp_health(
    evidence_links: list[_MockLink],
    solutions: list[_MockSolution],
) -> dict:
    """Replica of opportunity health calculations in load_dashboard()."""
    return {
        "with_evidence":   len(set(lnk.opportunity_id for lnk in evidence_links)),
        "with_solutions":  len(set(s.opportunity_id for s in solutions)),
        "testing":         sum(1 for s in solutions if s.status == "Testing"),
    }


class TestOpportunityHealthCounts:
    def test_no_evidence_no_solutions(self):
        result = _opp_health([], [])
        assert result == {"with_evidence": 0, "with_solutions": 0, "testing": 0}

    def test_each_link_counted_once_per_opportunity(self):
        """Two quotes for the same opportunity → still counts as 1."""
        links = [_MockLink(1), _MockLink(1), _MockLink(2)]
        result = _opp_health(links, [])
        assert result["with_evidence"] == 2

    def test_distinct_evidence_opportunities(self):
        links = [_MockLink(i) for i in range(5)]
        result = _opp_health(links, [])
        assert result["with_evidence"] == 5

    def test_solutions_counted_per_opportunity(self):
        """Two solutions for the same opportunity → still counts as 1."""
        solutions = [
            _MockSolution(1, opportunity_id=10, status="Ideation"),
            _MockSolution(2, opportunity_id=10, status="Testing"),
            _MockSolution(3, opportunity_id=20, status="Ideation"),
        ]
        result = _opp_health([], solutions)
        assert result["with_solutions"] == 2

    def test_testing_solutions_counted_correctly(self):
        solutions = [
            _MockSolution(1, opportunity_id=10, status="Testing"),
            _MockSolution(2, opportunity_id=11, status="Testing"),
            _MockSolution(3, opportunity_id=12, status="Ideation"),
            _MockSolution(4, opportunity_id=13, status="Shipped"),
        ]
        result = _opp_health([], solutions)
        assert result["testing"] == 2

    def test_only_testing_status_counted(self):
        for status in ["Ideation", "Shipped", "Discarded"]:
            solutions = [_MockSolution(1, opportunity_id=1, status=status)]
            result = _opp_health([], solutions)
            assert result["testing"] == 0, f"Status '{status}' should not count as Testing"

    def test_all_solutions_testing(self):
        solutions = [_MockSolution(i, opportunity_id=i, status="Testing") for i in range(4)]
        result = _opp_health([], solutions)
        assert result["testing"] == 4
        assert result["with_solutions"] == 4

    def test_opportunity_can_have_evidence_and_solutions(self):
        links = [_MockLink(1), _MockLink(2)]
        solutions = [_MockSolution(1, opportunity_id=1, status="Testing")]
        result = _opp_health(links, solutions)
        assert result["with_evidence"] == 2
        assert result["with_solutions"] == 1
        assert result["testing"] == 1

    def test_with_solutions_empty_when_no_solutions(self):
        links = [_MockLink(i) for i in range(5)]
        result = _opp_health(links, [])
        assert result["with_solutions"] == 0
        assert result["testing"] == 0
