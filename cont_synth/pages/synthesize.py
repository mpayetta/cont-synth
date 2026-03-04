import reflex as rx
from cont_synth.state import State


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
        rx.input(
            placeholder="Persona (e.g., Consultant, MD)",
            value=State.persona_input,
            on_change=State.set_persona_input,
            width="100%",
            size="3",
            custom_attrs={"list": "persona-suggestions"},
        ),
        rx.el.datalist(
            rx.foreach(State.available_personas, lambda p: rx.el.option(value=p)),
            id="persona-suggestions",
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
                rx.icon("circle-alert", size=15, color="#EF476F"),
                rx.text(State.synthesis_error, size="2", color="#EF476F"),
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
            rx.icon("sparkles", size=16),
            "Run Dual-Engine Synthesis",
            on_click=State.run_synthesis,
            loading=State.is_processing,
            size="4",
            width="100%",
            color_scheme="violet",
        ),
        width="100%",
        max_width="900px",
        spacing="4",
        padding_top="20px",
    )
