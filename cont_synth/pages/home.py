import reflex as rx
from cont_synth.state import State, MatrixCell
from cont_synth.state.core import DashboardBarItem, RecentInterviewItem


# ── Helpers ────────────────────────────────────────────────────────────────────

def _stat_row(icon: str, icon_color: str, label: str, value_component: rx.Component) -> rx.Component:
    """A labeled stat row: icon + label on left, value component on right."""
    return rx.hstack(
        rx.icon(icon, size=14, color=icon_color),
        rx.text(label, size="3", color="var(--gray-12)"),
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
                    background_color="var(--blue-9)",
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
            color="var(--gray-12)",
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
        rx.text(item.date_str, size="2", color="var(--gray-12)", min_width="90px"),
        rx.spacer(),
        rx.hstack(
            rx.icon("quote", size=13, color="var(--gray-12)"),
            rx.text(item.quote_count.to_string(), " quotes", size="2", color="var(--gray-12)"),
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
                rx.icon("calendar-check", size=16, color="var(--blue-9)"),
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
                                    "#E5484D",
                                ),
                            ),
                        ),
                        rx.vstack(
                            rx.text("days since", size="2", color="var(--gray-12)"),
                            rx.text("last interview", size="2", color="var(--gray-12)"),
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
                rx.text("No interviews ingested yet.", color="var(--gray-12)", size="3"),
            ),
            rx.divider(),
            # 8-week bar chart
            rx.vstack(
                rx.hstack(
                    rx.text("Past 8 weeks", size="2", color="var(--gray-12)"),
                    rx.spacer(),
                    rx.hstack(
                        rx.text(
                            State.dashboard_total_interviews.to_string(),
                            weight="bold",
                            size="2",
                        ),
                        rx.text("total interviews", size="2", color="var(--gray-12)"),
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
                "circle-dashed", "var(--gray-12)",
                "Draft",
                rx.text(State.dashboard_exp_draft.to_string(), weight="bold", size="3"),
            ),
            _stat_row(
                "circle-play", "var(--blue-9)",
                "Running",
                rx.text(State.dashboard_exp_running.to_string(), weight="bold", size="3", color="var(--blue-9)"),
            ),
            _stat_row(
                "circle-check", "var(--gray-12)",
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
                            rx.icon("x", size=12, color="#E5484D"),
                            rx.text(
                                State.dashboard_exp_invalidated.to_string(),
                                " Invalidated",
                                size="2",
                                color="#E5484D",
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
                rx.text("Total opportunities", size="2", color="var(--gray-12)"),
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
                        color="var(--gray-12)",
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
                        color="var(--gray-12)",
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
                rx.icon("activity", size=16, color="var(--gray-12)"),
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
                        color="var(--gray-12)",
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


def _dashboard_matrix_cell(cell: MatrixCell) -> rx.Component:
    """Compact matrix cell for the dashboard view."""
    return rx.box(
        rx.vstack(
            rx.foreach(
                cell.opps,
                lambda item: rx.box(
                    rx.text(
                        item.theme,
                        size="1",
                        weight="bold",
                        color="var(--blue-11)",
                        overflow="hidden",
                        white_space="nowrap",
                        text_overflow="ellipsis",
                        max_width="100%",
                    ),
                    rx.text(
                        item.opportunity,
                        size="1",
                        color="var(--gray-12)",
                        style={
                            "overflow": "hidden",
                            "display": "-webkit-box",
                            "-webkit-line-clamp": "2",
                            "-webkit-box-orient": "vertical",
                        },
                    ),
                    padding="3px 5px",
                    border_radius="4px",
                    background_color="var(--blue-3)",
                    border="1px solid",
                    border_color="var(--blue-5)",
                    cursor="pointer",
                    width="100%",
                    on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
                    _hover={"opacity": "0.8"},
                ),
            ),
            spacing="1",
        ),
        min_height="52px",
        padding="5px",
        background_color=rx.cond(
            cell.is_sweet_spot, "var(--green-2)", "var(--gray-1)"
        ),
        border="1px solid",
        border_color=rx.cond(
            cell.is_sweet_spot, "var(--green-4)", "var(--gray-4)"
        ),
        border_radius="4px",
        overflow="hidden",
        width="100%",
    )


def _priority_matrix_widget() -> rx.Component:
    """Compact 5×5 priority matrix for the dashboard."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon("grid-2x2", size=16, color="var(--green-9)"),
                rx.text("Priority Matrix", weight="bold", size="4"),
                rx.spacer(),
                rx.flex(
                    rx.box(
                        width="10px", height="10px",
                        background_color="var(--green-3)",
                        border="1px solid var(--green-5)",
                        border_radius="2px",
                        flex_shrink="0",
                    ),
                    rx.text("Priority zone", size="1", color="var(--gray-12)"),
                    spacing="1", align="center",
                ),
                rx.button(
                    "Full Ledger →",
                    variant="ghost",
                    size="1",
                    color_scheme="gray",
                    on_click=State.handle_navigation("ledger"),
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.divider(),
            # Column headers (Impact 1→5)
            rx.flex(
                rx.box(width="28px", flex_shrink="0"),
                rx.grid(
                    rx.text("I:1", size="1", color="var(--gray-11)", text_align="center"),
                    rx.text("I:2", size="1", color="var(--gray-11)", text_align="center"),
                    rx.text("I:3", size="1", color="var(--gray-11)", text_align="center"),
                    rx.text("I:4", size="1", color="var(--gray-11)", text_align="center"),
                    rx.text("I:5", size="1", color="var(--gray-11)", text_align="center"),
                    columns="5",
                    width="100%",
                    spacing="1",
                ),
                align="center",
                spacing="1",
                width="100%",
            ),
            # Y-axis labels + 5×5 grid
            rx.flex(
                rx.vstack(
                    rx.text("G:5", size="1", color="var(--gray-11)", width="28px", text_align="center"),
                    rx.text("G:4", size="1", color="var(--gray-11)", width="28px", text_align="center"),
                    rx.text("G:3", size="1", color="var(--gray-11)", width="28px", text_align="center"),
                    rx.text("G:2", size="1", color="var(--gray-11)", width="28px", text_align="center"),
                    rx.text("G:1", size="1", color="var(--gray-11)", width="28px", text_align="center"),
                    justify="between",
                    height="280px",
                    flex_shrink="0",
                ),
                rx.grid(
                    rx.foreach(State.matrix_cells, _dashboard_matrix_cell),
                    columns="5",
                    spacing="1",
                    width="100%",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            width="100%",
            spacing="3",
        ),
        width="100%",
        height="100%",
    )


def _quick_actions() -> rx.Component:
    """Primary CTA buttons."""
    return rx.hstack(
        rx.cond(
            ~State.is_viewer,
            rx.button(
                rx.icon("sparkles", size=15),
                "Synthesize Interview",
                color_scheme="blue",
                variant="solid",
                size="2",
                on_click=State.handle_navigation("synthesize"),
            ),
        ),
        rx.cond(
            ~State.is_viewer,
            rx.button(
                rx.icon("target", size=15),
                "Interview Prep",
                color_scheme="gray",
                variant="soft",
                size="2",
                on_click=State.handle_navigation("prep"),
            ),
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
                rx.heading(State.active_product_name, " Dashboard", size="6", weight="bold"),
                rx.text(
                    "Continuous Discovery requires ≥1 customer interview per week.",
                    color="var(--gray-12)",
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
        # Matrix + recent interviews side by side
        rx.grid(
            _priority_matrix_widget(),
            _recent_activity_widget(),
            template_columns="2fr 1fr",
            gap="16px",
            width="100%",
            align_items="start",
        ),
        width="100%",
        max_width="1200px",
        spacing="5",
        padding_top="20px",
        align="start",
    )
