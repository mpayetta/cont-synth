import reflex as rx
from cont_synth.state import State, InterviewHistoryItem


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
                rx.text("—", size="2", color="var(--gray-7)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.duration_minutes > 0,
                rx.text(item.duration_minutes.to_string(), " min", size="2"),
                rx.text("—", size="2", color="var(--gray-7)"),
            )
        ),
        rx.table.cell(
            rx.cond(
                item.participants != "",
                rx.text(item.participants, size="2"),
                rx.text("—", size="2", color="var(--gray-7)"),
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


def render_logs() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Interview Logs", weight="bold", size="6"),
            rx.text(
                "View ingested interviews and inspect their full transcripts and extracted evidence.",
                color="gray",
                size="3",
            ),
            margin_bottom="10px",
        ),
        rx.divider(),
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
        width="100%",
        max_width="1200px",
        spacing="4",
        padding_top="20px",
    )
