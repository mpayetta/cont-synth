import reflex as rx
from cont_synth.state import State
from cont_synth.state.core import DashboardBarItem, RecentInterviewItem


# ── Helpers ────────────────────────────────────────────────────────────────────

def _stat_row(icon: str, icon_color: str, label: str, value_component: rx.Component) -> rx.Component:
    """A labeled stat row: icon + label on left, value component on right."""
    return rx.hstack(
        rx.icon(icon, size=14, color=icon_color),
        rx.text(label, size="3", color="var(--gray-11)"),
        rx.spacer(),
        value_component,
        width="100%",
        align="center",
    )


def _render_bar(item: DashboardBarItem) -> rx.Component:
    """One column of the weekly sparkline bar chart."""
    return rx.vstack(
        # Bar grows from bottom inside a fixed-height container
        rx.box(
            rx.cond(
                item.count > 0,
                rx.box(
                    width="100%",
                    height=item.height_css,
                    background_color="var(--blue-8)",
                    border_radius="3px 3px 0 0",
                ),
                rx.box(
                    width="100%",
                    height="3px",
                    background_color="var(--gray-4)",
                    border_radius="2px",
                ),
            ),
            width="100%",
            height="48px",
            display="flex",
            flex_direction="column",
            justify_content="flex-end",
            align_items="stretch",
        ),
        rx.text(
            item.week_label,
            size="1",
            color="var(--gray-7)",
            text_align="center",
            white_space="nowrap",
        ),
        spacing="1",
        align="center",
        flex="1",
        min_width="0",
    )


def _render_recent_interview(item: RecentInterviewItem) -> rx.Component:
    """One row in the recent activity feed."""
    return rx.hstack(
        rx.badge(item.persona, color_scheme=item.persona_color, variant="soft", size="2"),
        rx.text(item.date_str, size="2", color="var(--gray-9)", min_width="90px"),
        rx.spacer(),
        rx.hstack(
            rx.icon("quote", size=13, color="var(--gray-7)"),
            rx.text(item.quote_count.to_string(), " quotes", size="2", color="var(--gray-9)"),
            spacing="1",
            align="center",
        ),
        rx.button(
            rx.icon("eye", size=13),
            "View",
            variant="ghost",
            color_scheme="gray",
            size="1",
            on_click=lambda: State.open_interview_detail(item.interview_id),
        ),
        width="100%",
        align="center",
        padding_y="10px",
    )


# ── Widgets ────────────────────────────────────────────────────────────────────

def _cadence_widget() -> rx.Component:
    """Interview cadence health — days since last + 8-week sparkline."""
    return rx.card(
        rx.vstack(
            # Header
            rx.hstack(
                rx.icon("calendar-check", size=16, color="var(--blue-10)"),
                rx.text("Interview Cadence", weight="bold", size="4"),
                spacing="2",
                align="center",
            ),
            rx.divider(),
            # Big "days since" number
            rx.cond(
                State.dashboard_days_since_last >= 0,
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            State.dashboard_days_since_last.to_string(),
                            size="9",
                            weight="bold",
                            color=rx.cond(
                                State.dashboard_days_since_last < 7,
                                "var(--green-11)",
                                rx.cond(
                                    State.dashboard_days_since_last <= 14,
                                    "var(--amber-11)",
                                    "var(--red-11)",
                                ),
                            ),
                        ),
                        rx.vstack(
                            rx.text("days since", size="2", color="var(--gray-9)"),
                            rx.text("last interview", size="2", color="var(--gray-9)"),
                            spacing="0",
                            align="start",
                        ),
                        align="end",
                        spacing="2",
                    ),
                    rx.cond(
                        State.dashboard_days_since_last < 7,
                        rx.badge("On track ✓", color_scheme="green", variant="soft"),
                        rx.cond(
                            State.dashboard_days_since_last <= 14,
                            rx.badge("Behind — schedule one soon", color_scheme="amber", variant="soft"),
                            rx.badge("Cadence at risk — act now", color_scheme="red", variant="soft"),
                        ),
                    ),
                    spacing="2",
                    align="start",
                ),
                rx.text("No interviews ingested yet.", color="var(--gray-9)", size="3"),
            ),
            rx.divider(),
            # 8-week bar chart
            rx.vstack(
                rx.hstack(
                    rx.text("Past 8 weeks", size="2", color="var(--gray-9)"),
                    rx.spacer(),
                    rx.hstack(
                        rx.text(
                            State.dashboard_total_interviews.to_string(),
                            weight="bold",
                            size="2",
                        ),
                        rx.text("total interviews", size="2", color="var(--gray-9)"),
                        spacing="1",
                        align="baseline",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.hstack(
                    rx.foreach(State.dashboard_weekly_bars, _render_bar),
                    width="100%",
                    spacing="1",
                    align="end",
                ),
                spacing="2",
                width="100%",
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def _experiment_widget() -> rx.Component:
    """Experiment pipeline counts by status."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("flask-conical", size=16, color="var(--purple-10)"),
                rx.text("Experiment Pipeline", weight="bold", size="4"),
                spacing="2",
                align="center",
            ),
            rx.divider(),
            _stat_row(
                "circle-dashed", "var(--gray-8)",
                "Draft",
                rx.text(State.dashboard_exp_draft.to_string(), weight="bold", size="3"),
            ),
            _stat_row(
                "play-circle", "var(--blue-9)",
                "Running",
                rx.text(State.dashboard_exp_running.to_string(), weight="bold", size="3", color="var(--blue-11)"),
            ),
            _stat_row(
                "check-circle-2", "var(--gray-9)",
                "Concluded",
                rx.text(State.dashboard_exp_concluded.to_string(), weight="bold", size="3"),
            ),
            # Validated / Invalidated breakdown — only shown when there are concluded experiments
            rx.cond(
                State.dashboard_exp_concluded > 0,
                rx.box(
                    rx.hstack(
                        rx.hstack(
                            rx.icon("check", size=12, color="var(--green-10)"),
                            rx.text(
                                State.dashboard_exp_validated.to_string(),
                                " Validated",
                                size="2",
                                color="var(--green-11)",
                            ),
                            spacing="1",
                            align="center",
                        ),
                        rx.hstack(
                            rx.icon("x", size=12, color="var(--red-10)"),
                            rx.text(
                                State.dashboard_exp_invalidated.to_string(),
                                " Invalidated",
                                size="2",
                                color="var(--red-11)",
                            ),
                            spacing="1",
                            align="center",
                        ),
                        spacing="4",
                    ),
                    padding="8px 12px",
                    background_color="var(--gray-2)",
                    border="1px solid var(--gray-5)",
                    border_radius="6px",
                    margin_top="4px",
                ),
                rx.fragment(),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def _opp_health_widget() -> rx.Component:
    """Opportunity health snapshot."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("layers", size=16, color="var(--orange-10)"),
                rx.text("Opportunity Health", weight="bold", size="4"),
                spacing="2",
                align="center",
            ),
            rx.divider(),
            rx.hstack(
                rx.text("Total opportunities", size="2", color="var(--gray-9)"),
                rx.spacer(),
                rx.text(
                    State.dashboard_total_opps.to_string(),
                    weight="bold",
                    size="3",
                ),
                width="100%",
                align="center",
            ),
            rx.divider(size="1"),
            _stat_row(
                "quote", "var(--blue-9)",
                "With evidence",
                rx.hstack(
                    rx.text(
                        State.dashboard_opps_with_evidence.to_string(),
                        weight="bold",
                        size="3",
                        color="var(--blue-11)",
                    ),
                    rx.text(
                        " / ",
                        State.dashboard_total_opps.to_string(),
                        size="3",
                        color="var(--gray-9)",
                    ),
                    spacing="0",
                    align="baseline",
                ),
            ),
            _stat_row(
                "lightbulb", "var(--amber-9)",
                "With solutions",
                rx.hstack(
                    rx.text(
                        State.dashboard_opps_with_solutions.to_string(),
                        weight="bold",
                        size="3",
                        color="var(--amber-11)",
                    ),
                    rx.text(
                        " / ",
                        State.dashboard_total_opps.to_string(),
                        size="3",
                        color="var(--gray-9)",
                    ),
                    spacing="0",
                    align="baseline",
                ),
            ),
            _stat_row(
                "flask-conical", "var(--purple-9)",
                "Solutions in Testing",
                rx.text(
                    State.dashboard_solutions_testing.to_string(),
                    weight="bold",
                    size="3",
                    color="var(--purple-11)",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def _recent_activity_widget() -> rx.Component:
    """Last 5 ingested interviews activity feed."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("activity", size=16, color="var(--gray-10)"),
                rx.text("Recent Interviews", weight="bold", size="4"),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.divider(),
            rx.cond(
                State.dashboard_recent_interviews.length() > 0,
                rx.vstack(
                    rx.foreach(State.dashboard_recent_interviews, _render_recent_interview),
                    width="100%",
                    spacing="0",
                ),
                rx.box(
                    rx.text(
                        "No interviews ingested yet. Synthesize your first interview to get started.",
                        color="var(--gray-9)",
                        size="2",
                    ),
                    padding_y="8px",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def _quick_actions() -> rx.Component:
    """Primary CTA buttons."""
    return rx.hstack(
        rx.button(
            rx.icon("sparkles", size=15),
            "Synthesize Interview",
            color_scheme="blue",
            variant="solid",
            size="2",
            on_click=State.handle_navigation("synthesize"),
        ),
        rx.button(
            rx.icon("target", size=15),
            "Interview Prep",
            color_scheme="gray",
            variant="soft",
            size="2",
            on_click=State.handle_navigation("prep"),
        ),
        rx.button(
            rx.icon("table", size=15),
            "Opportunity Ledger",
            color_scheme="gray",
            variant="soft",
            size="2",
            on_click=State.handle_navigation("ledger"),
        ),
        spacing="3",
        flex_wrap="wrap",
        align="center",
    )


# ── Page root ──────────────────────────────────────────────────────────────────

def render_home() -> rx.Component:
    return rx.vstack(
        # Page header + quick actions
        rx.hstack(
            rx.vstack(
                rx.heading("Dashboard", size="6", weight="bold"),
                rx.text(
                    "Continuous Discovery requires ≥1 customer interview per week.",
                    color="var(--gray-9)",
                    size="3",
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            _quick_actions(),
            width="100%",
            align="start",
            flex_wrap="wrap",
            gap="4",
        ),
        rx.divider(),
        # Top-row widgets
        rx.grid(
            _cadence_widget(),
            _experiment_widget(),
            _opp_health_widget(),
            columns="3",
            gap="16px",
            width="100%",
        ),
        # Recent activity
        _recent_activity_widget(),
        width="100%",
        max_width="1200px",
        spacing="5",
        padding_top="20px",
        align="start",
    )
