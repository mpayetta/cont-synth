import reflex as rx
from cont_synth.state import State, InterviewHistoryItem

def show_history_row(item: InterviewHistoryItem):
    return rx.table.row(
        rx.table.cell(item.interview_id, weight="bold"),
        rx.table.cell(rx.badge(item.persona, color_scheme="gray", variant="solid")),
        rx.table.cell(item.date_logged),
        rx.table.cell(rx.text(item.snippet, color="gray", size="2")),
        rx.table.cell(
            rx.button(
                rx.icon("trash", size=16), 
                "Delete", 
                color_scheme="red", 
                variant="soft", 
                on_click=lambda: State.delete_interview(item.interview_id)
            )
        )
    )

def render_logs() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Raw Transcript Management.", weight="bold", size="6"),
            rx.text("View and delete ingested interviews to keep the Global Ledger clean.", color="gray", size="3"),
            margin_bottom="10px"
        ),
        rx.divider(),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell("ID"),
                rx.table.column_header_cell("Persona"),
                rx.table.column_header_cell("Date Logged"),
                rx.table.column_header_cell("Transcript Snippet"),
                rx.table.column_header_cell("Action"),
            )),
            rx.table.body(rx.foreach(State.interview_history, show_history_row)),
            width="100%", variant="surface"
        ),
        width="100%", max_width="1200px", spacing="4", padding_top="20px"
    )