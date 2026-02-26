import reflex as rx
from cont_synth.state import State

def render_prep() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Targeted Assumption Testing.", weight="bold", size="6"),
            rx.text("Select a persona to view your Battle Plan. Regenerate scripts when new evidence changes the landscape.", color="gray", size="3"),
            margin_bottom="10px"
        ),
        rx.divider(),
        rx.select(
            State.available_personas, 
            value=State.target_persona, 
            on_change=State.load_prep_for_persona,
            size="3", 
            width="100%"
        ),
        rx.button(
            rx.cond(
                State.prep_questions != "",
                "Regenerate Script (Overwrite)",
                "Generate New Script"
            ),
            on_click=State.generate_hostile_questions, 
            loading=State.is_prepping, 
            size="4", 
            width="100%", 
            color_scheme="red",
            variant=rx.cond(State.prep_questions != "", "outline", "solid")
        ),
        rx.cond(
            State.prep_questions != "", 
            rx.box(
                rx.flex(
                    rx.badge("Battle Plan", color_scheme="red", variant="solid"),
                    rx.text(f"Last Updated: {State.prep_last_updated}", color="gray", size="1"),
                    justify="between",
                    align="center",
                    margin_bottom="10px"
                ),
                rx.markdown(State.prep_questions), 
                padding="20px", 
                background_color="var(--gray-3)", 
                border_radius="8px", 
                width="100%", 
                margin_top="20px"
            )
        ),
        width="100%", max_width="900px", spacing="4", padding_top="20px"
    )