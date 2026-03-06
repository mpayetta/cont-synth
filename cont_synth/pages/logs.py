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


def _log_filter_bar() -> rx.Component:
    """Filter bar: date range + participant multi-select + clear."""
    return rx.flex(
        # Date from
        rx.vstack(
            rx.text("From", size="1", color="var(--gray-10)"),
            rx.input(
                type="date",
                value=State.interviews_log_date_from,
                on_change=State.set_interviews_log_date_from,
                size="2",
            ),
            spacing="1",
        ),
        # Date to
        rx.vstack(
            rx.text("To", size="1", color="var(--gray-10)"),
            rx.input(
                type="date",
                value=State.interviews_log_date_to,
                on_change=State.set_interviews_log_date_to,
                size="2",
            ),
            spacing="1",
        ),
        # Participant multi-select
        rx.vstack(
            rx.text("Participant", size="1", color="var(--gray-10)"),
            rx.popover.root(
                rx.popover.trigger(
                    rx.button(
                        rx.icon("users", size=14),
                        rx.cond(
                            State.interviews_log_filter_participants.length() == 0,
                            rx.text("All"),
                            rx.text(
                                State.interviews_log_filter_participants.length().to_string(),
                                " selected",
                            ),
                        ),
                        rx.icon("chevron-down", size=12),
                        variant=rx.cond(
                            State.interviews_log_filter_participants.length() > 0,
                            "soft",
                            "outline",
                        ),
                        color_scheme=rx.cond(
                            State.interviews_log_filter_participants.length() > 0,
                            "blue",
                            "gray",
                        ),
                        size="2",
                        gap="4px",
                    ),
                ),
                rx.popover.content(
                    rx.cond(
                        State.available_log_participants.length() == 0,
                        rx.text("No participants yet.", size="2", color="var(--gray-9)"),
                        rx.vstack(
                            rx.foreach(
                                State.available_log_participants,
                                lambda p: rx.flex(
                                    rx.checkbox(
                                        checked=State.interviews_log_filter_participants.contains(p),
                                        on_change=lambda _: State.toggle_log_filter_participant(p),
                                    ),
                                    rx.text(p, size="2"),
                                    spacing="2",
                                    align="center",
                                    cursor="pointer",
                                    on_click=State.toggle_log_filter_participant(p),
                                    width="100%",
                                    padding="4px 0",
                                ),
                            ),
                            spacing="1",
                            min_width="180px",
                        ),
                    ),
                    padding="10px",
                ),
            ),
            spacing="1",
        ),
        # Clear button
        rx.cond(
            State.interviews_log_filters_active,
            rx.vstack(
                rx.text(" ", size="1"),  # spacer to align with inputs
                rx.button(
                    rx.icon("x", size=12),
                    "Clear",
                    variant="ghost",
                    color_scheme="gray",
                    size="2",
                    on_click=State.clear_log_filters,
                ),
                spacing="1",
            ),
            rx.fragment(),
        ),
        gap="16px",
        align="end",
        wrap="wrap",
        padding_bottom="4px",
    )


def _log_pagination() -> rx.Component:
    """Prev / page label / Next controls."""
    return rx.flex(
        rx.button(
            rx.icon("chevron-left", size=14),
            "Prev",
            variant="outline",
            color_scheme="gray",
            size="2",
            on_click=State.interviews_log_prev_page,
            disabled=~State.interviews_log_has_prev,
        ),
        rx.flex(
            rx.text(State.interviews_log_page_label, size="2", color="var(--gray-11)"),
            rx.text(
                " · ",
                State.interviews_log_total.to_string(),
                " total",
                size="2",
                color="var(--gray-9)",
            ),
            align="center",
            gap="2px",
        ),
        rx.button(
            "Next",
            rx.icon("chevron-right", size=14),
            variant="outline",
            color_scheme="gray",
            size="2",
            on_click=State.interviews_log_next_page,
            disabled=~State.interviews_log_has_next,
        ),
        justify="between",
        align="center",
        width="100%",
        padding_top="8px",
    )


def _log_tab() -> rx.Component:
    return rx.vstack(
        _log_filter_bar(),
        rx.cond(
            State.interview_history.length() == 0,
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=32, color="var(--gray-9)"),
                    rx.text(
                        rx.cond(
                            State.interviews_log_filters_active,
                            "No interviews match your filters.",
                            "No interviews yet.",
                        ),
                        weight="medium",
                        color="var(--gray-9)",
                    ),
                    rx.cond(
                        State.interviews_log_filters_active,
                        rx.button(
                            "Clear filters",
                            variant="soft",
                            color_scheme="gray",
                            size="2",
                            on_click=State.clear_log_filters,
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    align="center",
                ),
                padding_y="60px",
                width="100%",
            ),
            rx.vstack(
                rx.table.root(
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
                ),
                _log_pagination(),
                spacing="0",
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
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
                        stroke="#30A46C",
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
                    rx.icon("check-circle", size=16, color="#30A46C"),
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
                    rx.icon("x-circle", size=16, color="#E5484D"),
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
