import reflex as rx
from cont_synth.state import State, ParticipantItem
from cont_synth.pages.ui import combo_box

_INPUT_STYLE = {
    "width": "100%",
    "padding": "0 12px",
    "height": "36px",
    "border": "1px solid var(--gray-6)",
    "border_radius": "6px",
    "background": "var(--color-surface)",
    "color": "var(--gray-12)",
    "font_size": "14px",
    "box_sizing": "border-box",
    "outline": "none",
    "_focus": {
        "border_color": "var(--blue-8)",
        "box_shadow": "0 0 0 1px var(--blue-8)",
    },
}


def _field(label: str, input_el: rx.Component) -> rx.Component:
    """Label + input, stacked, equal width."""
    return rx.vstack(
        rx.text(label, size="2", color="var(--gray-12)", weight="medium"),
        input_el,
        spacing="1",
        align_items="stretch",
        flex="1",
        min_width="0",
        width="100%",
    )


def _plain_input(placeholder: str, value, on_change) -> rx.Component:
    return rx.el.input(
        placeholder=placeholder,
        default_value=value,
        on_blur=on_change,
        style=_INPUT_STYLE,
    )



def _participant_form_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(
                rx.cond(
                    State.editing_participant_id > 0,
                    "Edit Participant",
                    "New Participant",
                ),
                weight="bold",
                size="3",
            ),
            # Row 1: Name | Persona
            rx.hstack(
                _field(
                    "Name *",
                    _plain_input("Full name", State.participant_form_name, State.set_participant_form_name),
                ),
                _field(
                    "Persona (role archetype)",
                    combo_box(
                        "e.g. VP of Engineering, Managing Director",
                        State.participant_form_persona,
                        State.set_participant_form_persona,
                        "participant_persona",
                        State.filtered_participant_personas,
                    ),
                ),
                spacing="4",
                width="100%",
                align_items="start",
            ),
            # Team member toggle
            rx.hstack(
                rx.checkbox(
                    checked=State.participant_form_is_team_member,
                    on_change=State.set_participant_form_is_team_member,
                    size="2",
                ),
                rx.vstack(
                    rx.text("Product team member (interviewer)", size="2", weight="medium"),
                    rx.text(
                        "Check this if they are part of your team, not a customer being researched.",
                        size="1",
                        color="var(--gray-12)",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="3",
                align="start",
                width="100%",
            ),
            # Row 2: Segment | Recruited Via
            rx.hstack(
                _field(
                    "Segment",
                    combo_box(
                        "e.g. Enterprise, SMB, Mid-Market",
                        State.participant_form_segment,
                        State.set_participant_form_segment,
                        "participant_segment",
                        State.filtered_participant_segments,
                    ),
                ),
                _field(
                    "Recruited Via",
                    combo_box(
                        "e.g. LinkedIn, Customer Success, Referral",
                        State.participant_form_recruited_via,
                        State.set_participant_form_recruited_via,
                        "participant_recruited_via",
                        State.filtered_participant_recruited_vias,
                    ),
                ),
                spacing="4",
                width="100%",
                align_items="start",
            ),
            # Row 3: Notes (full width)
            _field(
                "Notes",
                rx.el.textarea(
                    placeholder="Any context about this participant...",
                    default_value=State.participant_form_notes,
                    on_blur=State.set_participant_form_notes,
                    width="100%",
                    style={
                        **_INPUT_STYLE,
                        "height": "80px",
                        "padding": "8px 12px",
                        "resize": "vertical",
                    },
                ),
            ),
            # Actions
            rx.hstack(
                rx.button("Save", color_scheme="blue", size="2", on_click=State.save_participant),
                rx.button("Cancel", variant="soft", color_scheme="gray", size="2", on_click=State.cancel_participant_form),
                spacing="3",
            ),
            spacing="4",
            width="100%",
        ),
        width="100%",
        padding="20px 24px",
    )


def _participant_row(item: ParticipantItem) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.name, weight="medium", size="2")),
        rx.table.cell(
            rx.cond(
                item.is_team_member,
                rx.badge("Interviewer", color_scheme="gray", variant="soft", size="1"),
                rx.badge("User", color_scheme="blue", variant="soft", size="1"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.persona_name != "",
                rx.badge(
                    item.persona_name,
                    color_scheme=item.persona_color,
                    variant="soft",
                    size="1",
                ),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.segment != "",
                rx.badge(item.segment, color_scheme="gray", variant="soft", size="1"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.recruited_via != "",
                rx.text(item.recruited_via, size="2"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.interview_count > 5,
                rx.badge(
                    item.interview_count.to_string(),
                    color_scheme="orange",
                    variant="soft",
                    size="1",
                ),
                rx.badge(
                    item.interview_count.to_string(),
                    color_scheme="blue",
                    variant="soft",
                    size="1",
                ),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.last_interviewed != "",
                rx.text(item.last_interviewed, size="2"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.notes != "",
                rx.text(
                    item.notes,
                    size="2",
                    max_width="180px",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                    display="block",
                    color="var(--gray-12)",
                ),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(
            rx.hstack(
                rx.icon_button(
                    rx.icon("pencil", size=14),
                    variant="ghost",
                    color_scheme="gray",
                    size="1",
                    on_click=lambda: State.start_edit_participant(item.id),
                ),
                rx.alert_dialog.root(
                    rx.alert_dialog.trigger(
                        rx.icon_button(
                            rx.icon("trash-2", size=14),
                            variant="ghost",
                            color_scheme="red",
                            size="1",
                        )
                    ),
                    rx.alert_dialog.content(
                        rx.alert_dialog.title("Delete Participant"),
                        rx.alert_dialog.description(
                            "Remove this participant? Their interview links will also be removed, but the interviews themselves are kept.",
                            size="2",
                        ),
                        rx.flex(
                            rx.alert_dialog.cancel(
                                rx.button("Cancel", variant="soft", color_scheme="gray")
                            ),
                            rx.alert_dialog.action(
                                rx.button(
                                    "Delete",
                                    color_scheme="red",
                                    on_click=lambda: State.delete_participant(item.id),
                                )
                            ),
                            gap="3",
                            justify="end",
                            margin_top="16px",
                        ),
                    ),
                ),
                spacing="1",
            ),
            padding_right="8px",
        ),
    )


def render_participants() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.text("Participants", weight="bold", size="6"),
            rx.text(
                "Track who you've talked to. Customers only by default — use the toggle to include interviewers. Orange badge = 6+ interviews (over-indexed voice).",
                color="var(--gray-12)",
                size="3",
            ),
            spacing="1",
            align_items="start",
            width="100%",
            margin_bottom="4px",
        ),
        rx.divider(),
        rx.hstack(
            rx.spacer(),
            rx.button(
                rx.cond(
                    State.show_team_members,
                    rx.hstack(rx.icon("eye-off", size=14), rx.text("Hide interviewers"), spacing="2", align="center"),
                    rx.hstack(rx.icon("eye", size=14), rx.text("Show interviewers"), spacing="2", align="center"),
                ),
                variant="ghost",
                color_scheme="gray",
                size="2",
                on_click=State.toggle_show_team_members,
            ),
            rx.button(
                rx.icon("user-plus", size=14),
                "Add Participant",
                color_scheme="blue",
                variant="soft",
                size="2",
                on_click=State.open_add_participant,
            ),
            width="100%",
            padding_y="4px",
            spacing="3",
            align="center",
        ),
        rx.cond(
            State.is_participant_form_open,
            _participant_form_card(),
            rx.fragment(),
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Name"),
                    rx.table.column_header_cell("Type"),
                    rx.table.column_header_cell("Persona"),
                    rx.table.column_header_cell("Segment"),
                    rx.table.column_header_cell("Recruited Via"),
                    rx.table.column_header_cell("Interviews"),
                    rx.table.column_header_cell("Last Interviewed"),
                    rx.table.column_header_cell("Notes"),
                    rx.table.column_header_cell(""),
                )
            ),
            rx.table.body(rx.foreach(State.filtered_participants, _participant_row)),
            width="100%",
            variant="surface",
        ),
        width="100%",
        max_width="1200px",
        spacing="4",
        padding_top="20px",
    )
