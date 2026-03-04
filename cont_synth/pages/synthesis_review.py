import reflex as rx
from cont_synth.state import State, PendingOppItem, PendingParticipantItem


def _coach_feedback_item(text: str) -> rx.Component:
    return rx.text("· ", text, size="2", color="var(--gray-12)")


def _render_coach_panel() -> rx.Component:
    """Coach's Corner card shown below the opportunity list during synthesis review."""
    return rx.cond(
        State.pending_coach_score > 0,
        rx.vstack(
            # Header row
            rx.hstack(
                rx.icon("graduation-cap", size=16, color="#8338EC"),
                rx.text(
                    "Coach's Corner",
                    size="2",
                    weight="bold",
                    color="#8338EC",
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                ),
                align="center",
                width="100%",
                spacing="2",
            ),
            # Keep Doing
            rx.cond(
                State.pending_coach_keep.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.icon("check-circle", size=13, color="#06D6A0"),
                        rx.text(
                            "Keep Doing",
                            size="1",
                            weight="bold",
                            color="#06D6A0",
                            text_transform="uppercase",
                            letter_spacing="0.05em",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.foreach(State.pending_coach_keep, _coach_feedback_item),
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
                State.pending_coach_stop.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.icon("x-circle", size=13, color="#EF476F"),
                        rx.text(
                            "Stop Doing",
                            size="1",
                            weight="bold",
                            color="#EF476F",
                            text_transform="uppercase",
                            letter_spacing="0.05em",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.foreach(State.pending_coach_stop, _coach_feedback_item),
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
                State.pending_coach_start.length() > 0,
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
                    rx.foreach(State.pending_coach_start, _coach_feedback_item),
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
            background_color="rgba(131, 56, 236, 0.04)",
            border_radius="10px",
            border="1px solid rgba(131, 56, 236, 0.2)",
            align_items="stretch",
            width="100%",
        ),
        rx.fragment(),
    )


def _render_participant_role(item: PendingParticipantItem) -> rx.Component:
    """One participant chip with Customer / Team toggle buttons."""
    return rx.hstack(
        rx.text(item.name, size="2", weight="medium", color="var(--gray-12)"),
        rx.button(
            "Customer",
            size="1",
            color_scheme="blue",
            variant=rx.cond(item.role == "interviewee", "soft", "ghost"),
            on_click=lambda: State.set_participant_role(item.index, "interviewee"),
            cursor="pointer",
        ),
        rx.button(
            "Team",
            size="1",
            color_scheme="orange",
            variant=rx.cond(item.role == "interviewer", "soft", "ghost"),
            on_click=lambda: State.set_participant_role(item.index, "interviewer"),
            cursor="pointer",
        ),
        spacing="2",
        align="center",
        padding="5px 10px",
        background_color="var(--gray-2)",
        border_radius="6px",
        border="1px solid var(--gray-5)",
    )


def _transcript_header_meta() -> rx.Component:
    """Date, duration, and editable participant roles — shown above the transcript."""
    return rx.vstack(
        # Date + duration row (shown only when available)
        rx.cond(
            (State.pending_synthesis_duration > 0)
            | (State.pending_synthesis_interview_date != ""),
            rx.hstack(
                rx.cond(
                    State.pending_synthesis_interview_date != "",
                    rx.hstack(
                        rx.icon("calendar", size=12, color="var(--gray-12)"),
                        rx.text(
                            State.pending_synthesis_interview_date,
                            size="1",
                            color="var(--gray-12)",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    State.pending_synthesis_duration > 0,
                    rx.hstack(
                        rx.icon("clock", size=12, color="var(--gray-12)"),
                        rx.text(
                            State.pending_synthesis_duration.to_string(),
                            " min",
                            size="1",
                            color="var(--gray-12)",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                spacing="4",
                align="center",
            ),
            rx.fragment(),
        ),
        # Participants with role editor (shown only when participants were extracted)
        rx.cond(
            State.pending_synthesis_participants.length() > 0,
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
                    rx.text(
                        "· set each person's role before confirming",
                        size="1",
                        color="var(--gray-12)",
                        style={"font_style": "italic"},
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.flex(
                    rx.foreach(
                        State.pending_participants_with_roles,
                        _render_participant_role,
                    ),
                    wrap="wrap",
                    gap="2",
                ),
                spacing="2",
                align_items="start",
                width="100%",
                padding="10px 14px",
                background_color="var(--gray-2)",
                border_radius="8px",
                border="1px solid var(--gray-5)",
            ),
            rx.fragment(),
        ),
        spacing="2",
        align_items="start",
        width="100%",
    )


def render_pending_opp(opp: PendingOppItem) -> rx.Component:
    """Renders one AI-extracted opportunity with a checkbox, badges, and clickable evidence."""
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=opp.selected,
                on_change=lambda _: State.toggle_pending_opp(opp.index),
                color_scheme="blue",
                size="2",
            ),
            rx.vstack(
                # Statement + NEW/EXISTING badge
                rx.hstack(
                    rx.text(opp.opportunity_statement, size="2", weight="medium"),
                    rx.cond(
                        opp.matched_existing_id > 0,
                        rx.badge("EXISTING", color_scheme="amber", size="1", variant="soft"),
                        rx.badge("NEW", color_scheme="green", size="1", variant="soft"),
                    ),
                    align="start",
                    spacing="2",
                    flex_wrap="wrap",
                ),
                # "Matches existing" hint
                rx.cond(
                    opp.matched_existing_id > 0,
                    rx.text(
                        "Matches: ",
                        opp.matched_existing_statement,
                        size="1",
                        color="var(--amber-9)",
                        style={"font_style": "italic"},
                    ),
                    rx.fragment(),
                ),
                # Evidence quote — clickable to highlight in transcript
                rx.box(
                    rx.hstack(
                        rx.icon("quote", size=10, color="var(--blue-9)"),
                        rx.text(
                            opp.source_quote,
                            size="2",
                            color="var(--gray-12)",
                            style={"font_style": "italic"},
                        ),
                        spacing="1",
                        align="start",
                    ),
                    padding="12px 14px",
                    background_color="var(--blue-2)",
                    border_radius="8px",
                    border="1px solid var(--blue-6)",
                    cursor="pointer",
                    on_click=State.set_highlighted_quote(opp.source_quote),
                    _hover={"background_color": "var(--blue-3)"},
                    transition="all 0.15s",
                    width="100%",
                ),
                spacing="2",
                align_items="start",
                flex="1",
                min_width="0",
            ),
            align="start",
            spacing="3",
            width="100%",
        ),
        padding="12px",
        background_color=rx.cond(opp.selected, "var(--blue-2)", "var(--gray-2)"),
        border=rx.cond(
            opp.selected,
            "1px solid var(--blue-5)",
            "1px solid var(--gray-4)",
        ),
        border_radius="6px",
        transition="all 0.15s",
        width="100%",
    )


def render_synthesis_review() -> rx.Component:
    return rx.vstack(
        # Page header
        rx.hstack(
            rx.vstack(
                rx.text("Review Synthesis Results", weight="bold", size="6"),
                rx.text(
                    "Select the opportunities to ingest. Click an evidence quote to verify it in the transcript.",
                    color="gray",
                    size="3",
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.cond(
                    State.pending_coach_score > 0,
                    rx.badge(
                        "Coach Score: ",
                        State.pending_coach_score.to_string(),
                        "/10",
                        color_scheme=rx.cond(
                            State.pending_coach_score >= 8,
                            "green",
                            rx.cond(State.pending_coach_score >= 5, "amber", "red"),
                        ),
                        size="2",
                    ),
                    rx.badge(
                        "Quality: ",
                        State.pending_synthesis_quality.to_string(),
                        "/10",
                        color_scheme="blue",
                        size="2",
                    ),
                ),
                rx.badge(State.pending_synthesis_persona, color_scheme="purple", size="2"),
                spacing="2",
                align="center",
            ),
            align="start",
            width="100%",
        ),
        rx.divider(),
        # Two-column body
        rx.hstack(
            # ── Left: Full transcript ─────────────────────────────────────────
            rx.vstack(
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
                    rx.text(
                        "· click a quote on the right to highlight",
                        size="1",
                        color="var(--gray-12)",
                        style={"font_style": "italic"},
                    ),
                    align="center",
                    spacing="2",
                ),
                # Date, duration, and participant role editor
                _transcript_header_meta(),
                rx.box(
                    rx.html(State.synthesis_review_transcript_html),
                    width="100%",
                    height="calc(100vh - 340px)",
                    overflow_y="auto",
                    padding="16px",
                    background_color="var(--gray-2)",
                    border_radius="8px",
                    border="1px solid var(--gray-5)",
                    id="synthesis-transcript",
                ),
                spacing="3",
                flex="1",
                align_items="stretch",
                min_width="0",
            ),
            # ── Right: Opportunity review panel ───────────────────────────────
            rx.vstack(
                # Header OUTSIDE the card — aligns with the left panel's title row
                rx.hstack(
                    rx.text(
                        "Extracted Opportunities",
                        size="2",
                        weight="bold",
                        color="var(--gray-12)",
                        text_transform="uppercase",
                        letter_spacing="0.05em",
                    ),
                    rx.spacer(),
                    rx.badge(
                        State.selected_opp_count.to_string(),
                        " / ",
                        State.pending_synthesis_opps.length().to_string(),
                        " selected",
                        color_scheme="gray",
                        size="1",
                    ),
                    width="100%",
                    align="center",
                ),
                # Card: opportunity list + actions
                rx.vstack(
                    # Scrollable opportunity list
                    rx.vstack(
                        rx.foreach(State.pending_synthesis_opps, render_pending_opp),
                        spacing="2",
                        width="100%",
                        overflow_y="auto",
                        max_height="calc(100vh - 360px)",
                        padding_right="4px",
                    ),
                    rx.divider(),
                    # Action buttons
                    rx.vstack(
                        rx.button(
                            rx.icon("check", size=14),
                            "Confirm & Ingest Selected",
                            color_scheme="blue",
                            size="3",
                            width="100%",
                            on_click=State.confirm_synthesis,
                            disabled=State.selected_opp_count == 0,
                        ),
                        rx.button(
                            "Cancel",
                            variant="ghost",
                            color_scheme="gray",
                            size="2",
                            width="100%",
                            on_click=State.cancel_synthesis_review,
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="3",
                    padding="20px",
                    background_color="var(--gray-2)",
                    border_radius="10px",
                    border="1px solid var(--gray-5)",
                    align_items="stretch",
                    width="100%",
                ),
                # Coach's Corner (shown when coach feedback was generated)
                _render_coach_panel(),
                spacing="3",
                width="400px",
                min_width="320px",
                max_width="440px",
                align_items="stretch",
            ),
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
