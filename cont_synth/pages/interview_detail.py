import reflex as rx
from cont_synth.state import State, DetailParticipantItem, CoachDetailItem


def _coach_item(item: CoachDetailItem) -> rx.Component:
    return rx.hstack(
        rx.text("· ", item.text, size="2", color="var(--gray-12)", flex="1"),
        rx.cond(
            item.first_timestamp != "",
            rx.badge(
                item.all_timestamps_str,
                color_scheme="gray",
                variant="surface",
                size="1",
                cursor="pointer",
                on_click=State.scroll_to_timestamp(item.first_timestamp),
                title="Jump to this moment in the transcript",
                _hover={"opacity": "0.7"},
            ),
            rx.fragment(),
        ),
        spacing="2",
        align="center",
        width="100%",
    )


def _coach_corner() -> rx.Component:
    """Coach feedback card shown below the evidence panel in the interview detail view."""
    # Shared title row — sits outside the card like the Evidence header
    title = rx.hstack(
        rx.icon("graduation-cap", size=16, color="var(--gray-12)",),
        rx.text(
            "Coach's Corner",
            size="2",
            weight="bold",
            color="var(--gray-12)",
            text_transform="uppercase",
            letter_spacing="0.05em",
        ),
        align="center",
        spacing="2",
        width="100%",
    )
    return rx.cond(
        State.interview_detail_coach_score > 0,
        rx.vstack(
            title,
            # Card — just the three bullet sections
            rx.vstack(
                # Keep Doing
                rx.cond(
                    State.interview_detail_coach_keep.length() > 0,
                    rx.vstack(
                        rx.hstack(
                            rx.icon("check-circle", size=13, color="#30A46C"),
                            rx.text(
                                "Keep Doing",
                                size="1",
                                weight="bold",
                                color="#30A46C",
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            spacing="1",
                            align="center",
                        ),
                        rx.foreach(State.interview_detail_coach_keep, _coach_item),
                        spacing="1",
                        align_items="start",
                        width="100%",
                        padding="10px 12px",
                        background_color="rgba(6, 214, 160, 0.08)",
                        border_radius="6px",
                        border="1px solid rgba(6, 214, 160, 0.3)",
                    ),
                    rx.fragment(),
                ),
                # Stop Doing
                rx.cond(
                    State.interview_detail_coach_stop.length() > 0,
                    rx.vstack(
                        rx.hstack(
                            rx.icon("x-circle", size=13, color="#E5484D"),
                            rx.text(
                                "Stop Doing",
                                size="1",
                                weight="bold",
                                color="#E5484D",
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            spacing="1",
                            align="center",
                        ),
                        rx.foreach(State.interview_detail_coach_stop, _coach_item),
                        spacing="1",
                        align_items="start",
                        width="100%",
                        padding="10px 12px",
                        background_color="rgba(239, 71, 111, 0.08)",
                        border_radius="6px",
                        border="1px solid rgba(239, 71, 111, 0.3)",
                    ),
                    rx.fragment(),
                ),
                # Start Doing
                rx.cond(
                    State.interview_detail_coach_start.length() > 0,
                    rx.vstack(
                        rx.hstack(
                            rx.icon("lightbulb", size=13, color="#F78C6B"),
                            rx.text(
                                "Start Doing",
                                size="1",
                                weight="bold",
                                color="#F78C6B",
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            spacing="1",
                            align="center",
                        ),
                        rx.foreach(State.interview_detail_coach_start, _coach_item),
                        spacing="1",
                        align_items="start",
                        width="100%",
                        padding="10px 12px",
                        background_color="rgba(247, 140, 107, 0.08)",
                        border_radius="6px",
                        border="1px solid rgba(247, 140, 107, 0.3)",
                    ),
                    rx.fragment(),
                ),
                spacing="3",
                padding="16px",
                border_radius="10px",
                align_items="stretch",
                width="100%",
                background_color="var(--gray-2)",

            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
        # No feedback yet — show generate button
        rx.vstack(
            title,
            rx.vstack(
                rx.text(
                    "No coaching analysis for this interview yet.",
                    size="2",
                    color="var(--gray-10)",
                ),
                rx.button(
                    rx.icon("sparkles", size=14),
                    rx.cond(
                        State.is_generating_coach,
                        "Generating...",
                        "Generate Coach Feedback",
                    ),
                    color_scheme="violet",
                    variant="soft",
                    size="2",
                    width="100%",
                    on_click=State.generate_coach_feedback,
                    loading=State.is_generating_coach,
                    disabled=State.is_generating_coach,
                ),
                spacing="3",
                padding="16px",
                background_color="var(--gray-2)",
                border_radius="10px",
                border="1px solid var(--gray-5)",
                align_items="stretch",
                width="100%",
            ),
            spacing="3",
            align_items="stretch",
            width="100%",
        ),
    )


def _detail_participant_chip(item: DetailParticipantItem) -> rx.Component:
    """Read-only participant chip showing their role badge."""
    return rx.hstack(
        rx.text(item.name, size="2", weight="medium", color="var(--gray-12)"),
        rx.cond(
            item.is_team_member,
            rx.badge("Team", color_scheme="amber", variant="soft", size="1"),
            rx.badge("Customer", color_scheme="blue", variant="soft", size="1"),
        ),
        spacing="2",
        align="center",
        padding="5px 10px",
        background_color="var(--gray-2)",
        border_radius="6px",
        border="1px solid var(--gray-5)",
    )


def _interview_info_panel() -> rx.Component:
    """Interview Info card: date, duration, and participants in one card with title outside."""
    return rx.vstack(
        # Title outside — matches Evidence Snippets / Coach's Corner style
        rx.hstack(
            rx.icon("info", size=16, color="var(--gray-12)"),
            rx.text(
                "Interview Info",
                size="2",
                weight="bold",
                color="var(--gray-12)",
                text_transform="uppercase",
                letter_spacing="0.05em",
            ),
            align="center",
            spacing="2",
        ),
        # Card
        rx.vstack(
            # Date + Duration
            rx.cond(
                (State.interview_detail_duration > 0)
                | (State.interview_detail_interview_date != ""),
                rx.hstack(
                    rx.cond(
                        State.interview_detail_interview_date != "",
                        rx.vstack(
                            rx.text(
                                "Interview Date",
                                size="1",
                                weight="bold",
                                color="var(--gray-10)",
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            rx.hstack(
                                rx.icon("calendar", size=13, color="var(--gray-12)"),
                                rx.text(
                                    State.interview_detail_interview_date,
                                    size="2",
                                    color="var(--gray-12)",
                                ),
                                spacing="1",
                                align="center",
                            ),
                            spacing="1",
                            align_items="start",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        State.interview_detail_duration > 0,
                        rx.vstack(
                            rx.text(
                                "Duration",
                                size="1",
                                weight="bold",
                                color="var(--gray-10)",
                                text_transform="uppercase",
                                letter_spacing="0.05em",
                            ),
                            rx.hstack(
                                rx.icon("clock", size=13, color="var(--gray-12)"),
                                rx.text(
                                    State.interview_detail_duration.to_string(),
                                    " min",
                                    size="2",
                                    color="var(--gray-12)",
                                ),
                                spacing="1",
                                align="center",
                            ),
                            spacing="1",
                            align_items="start",
                        ),
                        rx.fragment(),
                    ),
                    spacing="6",
                    align="start",
                ),
                rx.fragment(),
            ),
            # Participants
            rx.cond(
                State.interview_detail_participant_items.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.icon("users", size=13, color="var(--gray-12)"),
                        rx.text(
                            "Participants",
                            size="1",
                            weight="bold",
                            color="var(--gray-12)",
                            text_transform="uppercase",
                            letter_spacing="0.05em",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.flex(
                        rx.foreach(
                            State.interview_detail_participant_items,
                            _detail_participant_chip,
                        ),
                        wrap="wrap",
                        gap="3",
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                ),
                rx.fragment(),
            ),
            spacing="3",
            padding="14px 16px",
            background_color="var(--gray-2)",
            border_radius="8px",
            border="1px solid var(--gray-5)",
            align_items="start",
            width="100%",
        ),
        spacing="3",
        align_items="stretch",
        width="100%",
    )


def evidence_panel() -> rx.Component:
    """Right panel: evidence snippet navigator with prev/next controls."""
    return rx.vstack(
        # Header — outside the card so it lines up with the "FULL TRANSCRIPT" label
        rx.hstack(
            rx.icon("quote", size=16, color="var(--gray-12)"),
            rx.text(
                "Evidence Snippets",
                size="2",
                weight="bold",
                color="var(--gray-12)",
                text_transform="uppercase",
                letter_spacing="0.05em",
            ),
            align="center",
            spacing="2",
        ),
        # Card — starts at the same vertical level as the transcript box
        rx.vstack(
            # Empty state
            rx.cond(
                State.interview_detail_quotes.length() == 0,
                rx.box(
                    rx.text(
                        "No evidence snippets were extracted from this interview.",
                        color="var(--gray-12)",
                        size="2",
                    ),
                    width="100%",
                ),
                # Quote card + nav
                rx.vstack(
                    # Position indicator
                    rx.hstack(
                        rx.text(State.quote_position, size="1", color="var(--gray-12)"),
                        justify="end",
                        width="100%",
                    ),
                    # Active quote card — click to highlight in transcript
                    rx.box(
                        rx.vstack(
                            # Linked opportunity label
                            rx.cond(
                                State.active_quote.opportunity_statement != "",
                                rx.hstack(
                                    rx.icon("link", size=12, color="var(--blue-9)"),
                                    rx.text(
                                        State.active_quote.opportunity_statement,
                                        size="1",
                                        color="var(--blue-9)",
                                        weight="medium",
                                    ),
                                    align="center",
                                    spacing="1",
                                    margin_bottom="8px",
                                ),
                            ),
                            # Quote text
                            rx.text(
                                State.active_quote.text,
                                size="3",
                                color="var(--gray-12)",
                                style={"font_style": "italic"},
                            ),
                            spacing="1",
                            align_items="start",
                        ),
                        padding="16px",
                        background_color="var(--blue-2)",
                        border="1px solid var(--blue-6)",
                        border_radius="8px",
                        width="100%",
                        cursor="pointer",
                        on_click=State.set_highlighted_quote(State.active_quote.text),
                        _hover={"background_color": "var(--blue-3)"},
                        title="Click to highlight in transcript",
                    ),
                    # Prev / Next controls
                    rx.hstack(
                        rx.button(
                            rx.icon("chevron-left", size=16),
                            "Prev",
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            disabled=~State.has_prev_quote,
                            on_click=State.prev_quote,
                        ),
                        rx.spacer(),
                        rx.button(
                            "Next",
                            rx.icon("chevron-right", size=16),
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            disabled=~State.has_next_quote,
                            on_click=State.next_quote,
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.text(
                        "Click a card to highlight it in the transcript",
                        size="1",
                        color="var(--gray-12)",
                        style={"font_style": "italic"},
                        text_align="center",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            spacing="3",
            width="100%",
            padding="20px",
            background_color="var(--gray-2)",
            border_radius="10px",
            align_items="stretch",
        ),
        spacing="3",
        width="100%",
        align_items="stretch",
        min_width="280px",
        max_width="360px",
    )


def render_interview_detail() -> rx.Component:
    return rx.vstack(
        rx.hstack(
        # Back navigation
        rx.button(
            rx.icon("arrow-left", size=16),
            "Back to Interviews",
            variant="ghost",
            color_scheme="gray",
            size="2",
            on_click=State.handle_navigation("logs"),
            margin_bottom="4px",
            margin_right="8px",
            width="140px",
        ),
        rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.button(
                        rx.icon("trash", size=14),
                        "Delete Interview",
                        color_scheme="red",
                        variant="ghost",
                        size="2",
                        width="140px",
                    )
                ),
                rx.alert_dialog.content(
                    rx.alert_dialog.title("Delete Interview"),
                    rx.alert_dialog.description(
                        "Are you sure? This will permanently remove this interview and unlink all associated evidence. Opportunities that have no other evidence will also be removed.",
                        size="2",
                    ),
                    rx.flex(
                        rx.alert_dialog.cancel(
                            rx.button("Cancel", variant="soft", color_scheme="gray")
                        ),
                        rx.alert_dialog.action(
                            rx.button(
                                "Yes, delete it",
                                color_scheme="red",
                                on_click=State.delete_current_interview,
                            )
                        ),
                        spacing="3",
                        margin_top="16px",
                        justify="end",
                    ),
                ),
            ),
        ),
        # Header: persona badge + created-at date + interview ID + quality score
        rx.hstack(
            rx.badge(
                State.interview_detail_persona,
                color_scheme=State.interview_detail_persona_color,
                variant="soft",
                size="2",
            ),
            rx.text("Created at", color="var(--gray-10)", size="2"),
            rx.text(State.interview_detail_date, color="var(--gray-12)", size="2"),
            rx.text("·", color="var(--gray-12)", size="2"),
            rx.text(
                "Interview #",
                State.selected_interview_id.to_string(),
                color="var(--gray-12)",
                size="2",
            ),
            rx.spacer(),
            rx.cond(
                State.interview_detail_coach_score > 0,
                rx.badge(
                    "Score: ",
                    State.interview_detail_coach_score.to_string(),
                    "/10",
                    color_scheme=rx.cond(
                        State.interview_detail_coach_score >= 8,
                        "green",
                        rx.cond(State.interview_detail_coach_score >= 5, "amber", "red"),
                    ),
                    size="2",
                ),
                rx.cond(
                    State.interview_detail_quality > 0,
                    rx.badge(
                        "Quality: ",
                        State.interview_detail_quality.to_string(),
                        "/10",
                        color_scheme="blue",
                        size="2",
                    ),
                    rx.fragment(),
                ),
            ),
            align="center",
            spacing="2",
            width="100%",
        ),
        rx.divider(),
        # Two-column body — fills remaining viewport height; each column scrolls independently
        rx.hstack(
            # ── Left: Interview info + Full transcript ────────────────────────
            rx.vstack(
                _interview_info_panel(),
                # Transcript title sits directly above the transcript box
                rx.hstack(
                    rx.icon("file-text", size=16, color="var(--gray-12)"),
                    rx.text(
                        "Full Transcript",
                        size="2",
                        weight="bold",
                        color="var(--gray-12)",
                        text_transform="uppercase",
                        letter_spacing="0.05em",
                    ),
                    align="center",
                    spacing="2",
                    margin_top="16px",
                ),
                rx.box(
                    rx.html(State.detail_transcript_html),
                    width="100%",
                    flex="1",
                    min_height="0",
                    overflow_y="auto",
                    padding="16px",
                    background_color="var(--gray-2)",
                    border_radius="8px",
                    border="1px solid var(--gray-5)",
                    id="interview-transcript",
                ),
                spacing="3",
                flex="1",
                min_height="0",
                align_items="stretch",
            ),
            # ── Right: Evidence + Coach — scrolls independently ───────────────
            rx.vstack(
                evidence_panel(),
                _coach_corner(),
                spacing="4",
                min_width="280px",
                max_width="360px",
                align_items="stretch",
                overflow_y="auto",
                padding_bottom="20px",
            ),
            flex="1",
            min_height="0",
            overflow="hidden",
            align_items="stretch",
            spacing="5",
            width="100%",
        ),
        height="100%",
        overflow="hidden",
        width="100%",
        max_width="1400px",
        spacing="4",
        padding_top="20px",
        align_items="stretch",
    )
