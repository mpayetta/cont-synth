import reflex as rx
from cont_synth.state import State, InterviewHistoryItem
from cont_synth.state.core import CoachFreqItem


def show_history_row(item: InterviewHistoryItem):
    return rx.table.row(
        rx.table.cell(item.interview_id, weight="bold"),
        rx.table.cell(
            rx.badge(item.persona, color_scheme=item.persona_color, variant="soft")
        ),
        rx.table.cell(item.date_logged),
        rx.table.cell(
            rx.cond(
                item.interview_date != "",
                rx.text(item.interview_date, size="2"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.duration_minutes > 0,
                rx.text(item.duration_minutes.to_string(), " min", size="2"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.participants != "",
                rx.text(item.participants, size="2"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.button(
                rx.icon("eye", size=14),
                "View",
                variant="ghost",
                color_scheme="gray",
                size="2",
                on_click=lambda: State.open_interview_detail(item.interview_id),
            )
        ),
    )


def _freq_item(item: CoachFreqItem) -> rx.Component:
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
        rx.text("No coaching data yet.", color="var(--gray-9)", size="3", weight="medium"),
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


def _log_tab() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("ID"),
                rx.table.column_header_cell("Persona"),
                rx.table.column_header_cell("Date Logged"),
                rx.table.column_header_cell("Interview Date"),
                rx.table.column_header_cell("Duration"),
                rx.table.column_header_cell("Participants"),
                rx.table.column_header_cell(""),
            )
        ),
        rx.table.body(rx.foreach(State.interview_history, show_history_row)),
        width="100%",
        variant="surface",
    )


def _coach_tab() -> rx.Component:
    return rx.vstack(
        # Score Trend
        rx.vstack(
            rx.hstack(
                rx.icon("trending-up", size=16, color="var(--gray-12)"),
                rx.text("Score Trend", size="3", weight="bold", color="var(--gray-12)"),
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
                rx.recharts.line_chart(
                    rx.recharts.line(
                        data_key="score",
                        stroke="#06D6A0",
                        dot=True,
                        type_="monotone",
                        stroke_width=2,
                    ),
                    rx.recharts.x_axis(data_key="date", tick_size=12),
                    rx.recharts.y_axis(domain=[0, 10], tick_count=6, tick_size=12),
                    rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                    rx.recharts.tooltip(),
                    data=State.coach_score_history,
                    width="100%",
                    height=280,
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
        # Aggregated Patterns
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.icon("check-circle", size=16, color="#06D6A0"),
                    rx.text("Top Keep Doing", size="3", weight="bold", color="var(--gray-12)"),
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
            rx.vstack(
                rx.hstack(
                    rx.icon("x-circle", size=16, color="#EF476F"),
                    rx.text("Top Stop Doing", size="3", weight="bold", color="var(--gray-12)"),
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
        spacing="5",
        align_items="stretch",
        width="100%",
        padding_top="4px",
    )


def render_logs() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.text("Interviews", weight="bold", size="6"),
            rx.text(
                "Review your interview history and track coaching progress over time.",
                color="gray",
                size="3",
            ),
            spacing="1",
            margin_bottom="4px",
        ),
        rx.divider(),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Interview Log", value="log"),
                rx.tabs.trigger("Coach Dashboard", value="coach"),
            ),
            rx.tabs.content(_log_tab(), value="log", padding_top="16px"),
            rx.tabs.content(_coach_tab(), value="coach", padding_top="16px"),
            default_value="log",
            width="100%",
        ),
        width="100%",
        max_width="1200px",
        spacing="4",
        padding_top="20px",
        align_items="stretch",
    )
