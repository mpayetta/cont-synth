import reflex as rx
from cont_synth.state import State


def evidence_panel() -> rx.Component:
    """Right panel: evidence snippet navigator with prev/next controls."""
    return rx.vstack(
        # Header — outside the card so it lines up with the "FULL TRANSCRIPT" label
        rx.hstack(
            rx.icon("quote", size=16, color="var(--gray-9)"),
            rx.text(
                "Evidence Snippets",
                size="2",
                weight="bold",
                color="var(--gray-9)",
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
                        color="var(--gray-9)",
                        size="2",
                    ),
                    width="100%",
                ),
                # Quote card + nav
                rx.vstack(
                    # Position indicator
                    rx.hstack(
                        rx.text(State.quote_position, size="1", color="var(--gray-9)"),
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
                        color="var(--gray-8)",
                        style={"font_style": "italic"},
                        text_align="center",
                        width="100%",
                    ),
                    spacing="3",
                    width="100%",
                ),
            ),
            # Divider + delete
            rx.divider(margin_top="8px", margin_bottom="8px"),
            rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.button(
                        rx.icon("trash", size=14),
                        "Delete Interview",
                        color_scheme="red",
                        variant="soft",
                        size="2",
                        width="100%",
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
            spacing="3",
            width="100%",
            padding="20px",
            background_color="var(--gray-2)",
            border_radius="10px",
            border="1px solid var(--gray-5)",
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
        # Back navigation
        rx.button(
            rx.icon("arrow-left", size=16),
            "Back to Interviews",
            variant="ghost",
            color_scheme="gray",
            size="2",
            on_click=State.handle_navigation("logs"),
            margin_bottom="4px",
        ),
        # Header: persona + date + interview ID
        rx.hstack(
            rx.badge(
                State.interview_detail_persona,
                color_scheme=State.interview_detail_persona_color,
                variant="soft",
                size="2",
            ),
            rx.text(State.interview_detail_date, color="var(--gray-9)", size="2"),
            rx.text("·", color="var(--gray-7)", size="2"),
            rx.text(
                "Interview #",
                State.selected_interview_id.to_string(),
                color="var(--gray-9)",
                size="2",
            ),
            align="center",
            spacing="2",
        ),
        # Metadata row — only shown when at least one field is available
        rx.cond(
            (State.interview_detail_interview_date != "")
            | (State.interview_detail_duration > 0)
            | (State.interview_detail_participants != ""),
            rx.hstack(
                rx.cond(
                    State.interview_detail_interview_date != "",
                    rx.hstack(
                        rx.icon("calendar", size=13, color="var(--gray-9)"),
                        rx.text(State.interview_detail_interview_date, size="2", color="var(--gray-11)"),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.interview_detail_duration > 0,
                    rx.hstack(
                        rx.icon("clock", size=13, color="var(--gray-9)"),
                        rx.text(
                            State.interview_detail_duration.to_string(),
                            " min",
                            size="2",
                            color="var(--gray-11)",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.interview_detail_participants != "",
                    rx.hstack(
                        rx.icon("users", size=13, color="var(--gray-9)"),
                        rx.text(State.interview_detail_participants, size="2", color="var(--gray-11)"),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                spacing="4",
                align="center",
                padding="6px 12px",
                background_color="var(--gray-2)",
                border="1px solid var(--gray-4)",
                border_radius="6px",
                wrap="wrap",
            ),
        ),
        rx.divider(),
        # Two-column body
        rx.hstack(
            # Left: full transcript
            rx.vstack(
                rx.hstack(
                    rx.icon("file-text", size=16, color="var(--gray-9)"),
                    rx.text(
                        "Full Transcript",
                        size="2",
                        weight="bold",
                        color="var(--gray-9)",
                        text_transform="uppercase",
                        letter_spacing="0.05em",
                    ),
                    align="center",
                    spacing="2",
                ),
                rx.box(
                    rx.html(State.detail_transcript_html),
                    width="100%",
                    height="calc(100vh - 260px)",
                    overflow_y="auto",
                    padding="16px",
                    background_color="var(--gray-2)",
                    border_radius="8px",
                    border="1px solid var(--gray-5)",
                    id="interview-transcript",
                ),
                spacing="3",
                flex="1",
                align_items="stretch",
                min_width="0",
            ),
            # Right: evidence panel
            evidence_panel(),
            spacing="5",
            align_items="start",
            width="100%",
        ),
        width="100%",
        max_width="1400px",
        spacing="4",
        padding_top="20px",
        align_items="stretch",
    )
