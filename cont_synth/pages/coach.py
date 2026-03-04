import reflex as rx
from cont_synth.state import State
from cont_synth.state.core import CoachFreqItem


def _freq_item(item: CoachFreqItem) -> rx.Component:
    """Renders one aggregated coaching item with its frequency count."""
    return rx.hstack(
        rx.text(item.text, size="2", color="var(--gray-12)", flex="1"),
        rx.badge(
            item.count.to_string(),
            "×",
            color_scheme="gray",
            variant="soft",
            size="1",
        ),
        spacing="2",
        align="center",
        width="100%",
        padding="6px 10px",
        background_color="var(--gray-2)",
        border_radius="6px",
        border="1px solid var(--gray-4)",
    )


def _empty_chart_state() -> rx.Component:
    return rx.vstack(
        rx.icon("bar-chart-2", size=32, color="var(--gray-6)"),
        rx.text(
            "No coaching data yet.",
            color="var(--gray-9)",
            size="3",
            weight="medium",
        ),
        rx.text(
            "Import your first interview to start tracking your progress.",
            color="var(--gray-8)",
            size="2",
        ),
        spacing="2",
        align="center",
        padding="40px",
        width="100%",
    )


def render_coach() -> rx.Component:
    return rx.vstack(
        # Page header
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.icon("graduation-cap", size=24, color="var(--gray-12)"),
                    rx.text("Interview Coach", weight="bold", size="6"),
                    spacing="3",
                    align="center",
                ),
                rx.text(
                    "Track and improve your customer interviewing skills over time.",
                    color="gray",
                    size="3",
                ),
                spacing="1",
                align_items="start",
            ),
            width="100%",
        ),
        rx.divider(),

        # ── Score Trend Chart ──────────────────────────────────────────────────
        rx.vstack(
            rx.hstack(
                rx.icon("trending-up", size=16, color="var(--gray-12)"),
                rx.text(
                    "Score Trend",
                    size="3",
                    weight="bold",
                    color="var(--gray-12)",
                ),
                rx.text(
                    "· your interviewing quality over time",
                    size="2",
                    color="var(--gray-10)",
                    style={"font_style": "italic"},
                ),
                align="center",
                spacing="2",
            ),
            rx.cond(
                State.coach_score_history.length() == 0,
                _empty_chart_state(),
                rx.vstack(
                    rx.recharts.line_chart(
                        rx.recharts.line(
                            data_key="score",
                            stroke="#30A46C",
                            dot=True,
                            type_="monotone",
                            stroke_width=2,
                        ),
                        rx.recharts.x_axis(data_key="date", tick_size=12),
                        rx.recharts.y_axis(
                            domain=[0, 10],
                            tick_count=6,
                            tick_size=12,
                        ),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.tooltip(),
                        data=State.coach_score_history,
                        width="100%",
                        height=280,
                    ),
                    width="100%",
                ),
            ),
            spacing="3",
            padding="20px",
            background_color="var(--gray-2)",
            border_radius="10px",
            border="1px solid var(--gray-5)",
            align_items="stretch",
            width="100%",
        ),

        # ── Aggregated Patterns ────────────────────────────────────────────────
        rx.hstack(
            # Top Keep Doing
            rx.vstack(
                rx.hstack(
                    rx.icon("check-circle", size=16, color="#30A46C"),
                    rx.text(
                        "Top Keep Doing",
                        size="3",
                        weight="bold",
                        color="var(--gray-12)",
                    ),
                    rx.text(
                        "· most frequent strengths",
                        size="2",
                        color="var(--gray-10)",
                        style={"font_style": "italic"},
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.cond(
                    State.coach_top_keep_doing.length() == 0,
                    rx.text(
                        "No data yet — import interviews to see patterns.",
                        size="2",
                        color="var(--gray-9)",
                        style={"font_style": "italic"},
                    ),
                    rx.vstack(
                        rx.foreach(State.coach_top_keep_doing, _freq_item),
                        spacing="2",
                        width="100%",
                    ),
                ),
                spacing="3",
                padding="20px",
                background_color="rgba(6, 214, 160, 0.08)",
                border_radius="10px",
                border="1px solid rgba(6, 214, 160, 0.3)",
                align_items="stretch",
                flex="1",
            ),
            # Top Stop Doing
            rx.vstack(
                rx.hstack(
                    rx.icon("x-circle", size=16, color="#E5484D"),
                    rx.text(
                        "Top Stop Doing",
                        size="3",
                        weight="bold",
                        color="var(--gray-12)",
                    ),
                    rx.text(
                        "· most frequent bad habits",
                        size="2",
                        color="var(--gray-10)",
                        style={"font_style": "italic"},
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.cond(
                    State.coach_top_stop_doing.length() == 0,
                    rx.text(
                        "No data yet — import interviews to see patterns.",
                        size="2",
                        color="var(--gray-9)",
                        style={"font_style": "italic"},
                    ),
                    rx.vstack(
                        rx.foreach(State.coach_top_stop_doing, _freq_item),
                        spacing="2",
                        width="100%",
                    ),
                ),
                spacing="3",
                padding="20px",
                background_color="rgba(239, 71, 111, 0.08)",
                border_radius="10px",
                border="1px solid rgba(239, 71, 111, 0.3)",
                align_items="stretch",
                flex="1",
            ),
            spacing="4",
            align_items="start",
            width="100%",
        ),

        width="100%",
        max_width="1200px",
        spacing="5",
        padding_top="20px",
        align_items="stretch",
    )
