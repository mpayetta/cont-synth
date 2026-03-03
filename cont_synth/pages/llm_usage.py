import reflex as rx
from cont_synth.state import State, LlmUsageItem


def _stat_card(label: str, value: rx.Var) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(label, size="1", color="var(--gray-12)", weight="medium", text_transform="uppercase", letter_spacing="0.05em"),
            rx.text(value, size="7", weight="bold", color="var(--gray-12)"),
            spacing="1",
            align="start",
        ),
        padding="20px 24px",
        border_radius="8px",
        border="1px solid var(--gray-5)",
        background_color="var(--gray-1)",
        flex="1",
    )


def _operation_badge(operation: str) -> rx.Component:
    color = rx.match(
        operation,
        ("synthesis", "blue"),
        ("dedupe", "violet"),
        ("prep", "green"),
        "gray",
    )
    return rx.badge(operation, color_scheme=color, variant="soft")


def _show_usage_row(item: LlmUsageItem) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.created_at, size="2", color="var(--gray-12)")),
        rx.table.cell(
            rx.badge(item.model_name, color_scheme="gray", variant="outline", size="1")
        ),
        rx.table.cell(_operation_badge(item.operation)),
        rx.table.cell(
            rx.cond(
                item.interview_id > 0,
                rx.text(f"#{item.interview_id}", size="2", color="var(--gray-12)"),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(rx.text(item.prompt_tokens, size="2")),
        rx.table.cell(rx.text(item.output_tokens, size="2")),
        rx.table.cell(rx.text(item.total_tokens, size="2", weight="medium")),
    )


def render_llm_usage() -> rx.Component:
    return rx.vstack(
        # Header
        rx.box(
            rx.text("LLM Usage Dashboard", weight="bold", size="6"),
            rx.text(
                "Track token consumption and cost drivers across all AI operations.",
                color="gray",
                size="3",
            ),
            margin_bottom="10px",
        ),
        rx.divider(),
        # Summary stat cards
        rx.hstack(
            _stat_card("Total Tokens Used", State.llm_total_tokens),
            _stat_card("Synthesis Calls", State.llm_synthesis_count),
            _stat_card("Deduplication Calls", State.llm_dedupe_count),
            spacing="4",
            width="100%",
        ),
        # Usage table
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Date"),
                    rx.table.column_header_cell("Model"),
                    rx.table.column_header_cell("Operation"),
                    rx.table.column_header_cell("Interview"),
                    rx.table.column_header_cell("Prompt Tokens"),
                    rx.table.column_header_cell("Output Tokens"),
                    rx.table.column_header_cell("Total Tokens"),
                )
            ),
            rx.table.body(rx.foreach(State.llm_usage_logs, _show_usage_row)),
            width="100%",
            variant="surface",
        ),
        rx.cond(
            State.llm_usage_logs.length() == 0,
            rx.vstack(
                rx.icon("bar-chart-2", size=32, color="var(--gray-6)"),
                rx.text("No LLM calls recorded yet.", color="var(--gray-12)", size="3"),
                align="center",
                padding_y="40px",
                width="100%",
            ),
            rx.fragment(),
        ),
        width="100%",
        max_width="1200px",
        spacing="5",
        padding_top="20px",
    )
