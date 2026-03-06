import reflex as rx
from cont_synth.state import State
from cont_synth.pages.ui import combo_box


def render_synthesize() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Extract & Deduplicate.", weight="bold", size="6"),
            rx.text(
                "Upload raw interview transcripts to extract unmet needs and merge them into the knowledge base.",
                color="gray",
                size="3",
            ),
            margin_bottom="10px",
        ),
        rx.divider(),
        combo_box(
            placeholder="Persona (e.g., Consultant, MD)",
            value=State.persona_input,
            on_change=State.set_persona_input,
            field_id="synthesize_persona",
            suggestions=State.filtered_synthesize_personas,
            input_style={"height": "42px", "font_size": "16px"},
        ),
        rx.upload(
            rx.vstack(
                rx.button("Select File", color_scheme="blue", variant="outline"),
                rx.text("Drag & Drop PDF/DOCX/TXT", color="gray"),
                align_items="center",
            ),
            id="upload1",
            multiple=False,
            padding="20px",
            border="2px dashed #ccc",
            border_radius="8px",
            width="100%",
            on_drop=State.handle_upload(rx.upload_files(upload_id="upload1")),
        ),
        rx.text_area(
            placeholder="Transcript text...",
            value=State.transcript_text,
            on_change=State.set_transcript_text,
            min_height="300px",
            width="100%",
        ),
        rx.cond(
            State.synthesis_error != "",
            rx.hstack(
                rx.icon("circle-alert", size=15, color="#E5484D"),
                rx.text(State.synthesis_error, size="2", color="#E5484D"),
                padding="10px 14px",
                background_color="var(--red-2)",
                border="1px solid var(--red-6)",
                border_radius="6px",
                width="100%",
                align="center",
                spacing="2",
            ),
        ),
        rx.button(
            rx.cond(
                State.is_processing,
                rx.spinner(size="2"),
                rx.icon("sparkles", size=16),
            ),
            rx.cond(
                State.is_processing,
                State.synthesis_status,
                "Run Synthesis",
            ),
            on_click=State.run_synthesis,
            disabled=State.is_processing,
            size="4",
            width="100%",
            color_scheme="violet",
        ),
        rx.cond(
            State.is_processing,
            rx.hstack(
                rx.icon("arrow-left-right", size=13, color="var(--gray-9)"),
                rx.text(
                    "Feel free to navigate away — we'll notify you when it's ready.",
                    size="1",
                    color="var(--gray-9)",
                ),
                spacing="2",
                align="center",
                justify="center",
                width="100%",
            ),
        ),
        width="100%",
        max_width="900px",
        spacing="4",
        padding_top="20px",
    )
