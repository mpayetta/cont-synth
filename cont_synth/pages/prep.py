import reflex as rx
from cont_synth.state import State
from cont_synth.state.core import PrepOppItem, PrepExperimentItem


def _render_prep_opp_row(opp: PrepOppItem) -> rx.Component:
    """One opportunity row with a checkbox, theme badge, and statement."""
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=opp.selected,
                on_change=lambda _: State.toggle_prep_opportunity(opp.id),
                color_scheme="blue",
                size="2",
            ),
            rx.badge(opp.theme, color_scheme="gray", variant="soft", size="1"),
            rx.text(opp.statement, size="2", color="var(--gray-12)"),
            spacing="3",
            align="center",
            flex_wrap="wrap",
        ),
        padding="10px 12px",
        border_radius="6px",
        border="1px solid var(--gray-4)",
        background_color=rx.cond(opp.selected, "var(--blue-2)", "var(--gray-1)"),
        width="100%",
    )


def _render_prep_exp_row(exp: PrepExperimentItem) -> rx.Component:
    """One running experiment row with a checkbox, solution label, and assumption."""
    return rx.box(
        rx.hstack(
            rx.checkbox(
                checked=exp.selected,
                on_change=lambda _: State.toggle_prep_experiment(exp.id),
                color_scheme="violet",
                size="2",
            ),
            rx.vstack(
                rx.hstack(
                    rx.badge("Running", color_scheme="green", variant="soft", size="1"),
                    rx.text(exp.solution_name, size="1", color="var(--gray-10)", weight="medium"),
                    rx.text("·", size="1", color="var(--gray-7)"),
                    rx.text(exp.experiment_name, size="1", color="var(--gray-10)"),
                    spacing="2",
                    align="center",
                    flex_wrap="wrap",
                ),
                rx.text(
                    exp.assumption,
                    size="2",
                    color="var(--gray-12)",
                    style={"font_style": "italic"},
                ),
                spacing="1",
                align_items="start",
            ),
            spacing="3",
            align="start",
        ),
        padding="10px 12px",
        border_radius="6px",
        border="1px solid var(--gray-4)",
        background_color=rx.cond(exp.selected, "var(--violet-2)", "var(--gray-1)"),
        width="100%",
    )


def render_prep() -> rx.Component:
    return rx.vstack(
        # --- Header ---
        rx.box(
            rx.text("Interview Guide Prep", weight="bold", size="6"),
            rx.text(
                "Select opportunities to explore and experiment assumptions to probe. The guide will help you steer the conversation toward the areas of your tree that matter most right now.",
                color="gray",
                size="3",
            ),
            margin_bottom="10px",
        ),
        rx.divider(),

        # --- Opportunity Selector ---
        rx.vstack(
            rx.hstack(
                rx.text("Opportunities to explore", weight="medium", size="3"),
                rx.badge("Required for OST guide", color_scheme="blue", variant="soft", size="1"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Check the opportunities you want to probe in this interview. The guide will include discovery questions for each.",
                size="2",
                color="var(--gray-10)",
            ),
            rx.cond(
                State.prep_opportunities.length() > 0,
                rx.vstack(
                    rx.foreach(State.prep_opportunities, _render_prep_opp_row),
                    spacing="2",
                    width="100%",
                ),
                rx.box(
                    rx.text(
                        "No opportunities found. Add some in the Opportunity Ledger first.",
                        size="2",
                        color="var(--gray-9)",
                        style={"font_style": "italic"},
                    ),
                    padding="12px",
                    background_color="var(--gray-2)",
                    border_radius="6px",
                    width="100%",
                ),
            ),
            spacing="3",
            align_items="start",
            width="100%",
        ),

        # --- Experiment Assumptions Selector (only shown when selected opps have running experiments) ---
        rx.cond(
            State.visible_prep_experiments.length() > 0,
            rx.vstack(
                rx.hstack(
                    rx.text("Experiment assumptions to probe", weight="medium", size="3"),
                    rx.badge("Optional", color_scheme="gray", variant="soft", size="1"),
                    spacing="2",
                    align="center",
                ),
                rx.text(
                    "These are running experiments for your selected opportunities. Check the ones you want the guide to probe indirectly.",
                    size="2",
                    color="var(--gray-10)",
                ),
                rx.vstack(
                    rx.foreach(State.visible_prep_experiments, _render_prep_exp_row),
                    spacing="2",
                    width="100%",
                ),
                spacing="3",
                align_items="start",
                width="100%",
                padding_top="4px",
            ),
        ),

        # --- Persona Selector (optional context) ---
        rx.vstack(
            rx.hstack(
                rx.text("Customer persona", weight="medium", size="3"),
                rx.badge("Optional context", color_scheme="gray", variant="soft", size="1"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Optionally select a persona to give the LLM context about who you're interviewing. Required if generating the legacy battle plan (no opportunities selected).",
                size="2",
                color="var(--gray-10)",
            ),
            rx.select(
                State.prep_persona_options,
                value=rx.cond(State.target_persona != "", State.target_persona, "— None —"),
                on_change=State.load_prep_for_persona,
                size="3",
                width="100%",
            ),
            spacing="2",
            align_items="start",
            width="100%",
            padding_top="4px",
        ),

        # --- Generate Button ---
        rx.button(
            rx.cond(
                State.prep_questions != "",
                rx.cond(
                    State.selected_opportunity_ids.length() > 0,
                    "Regenerate Interview Guide",
                    "Regenerate Battle Plan",
                ),
                rx.cond(
                    State.selected_opportunity_ids.length() > 0,
                    "Generate Interview Guide",
                    "Generate Battle Plan",
                ),
            ),
            on_click=State.generate_hostile_questions,
            loading=State.is_prepping,
            size="4",
            width="100%",
            color_scheme=rx.cond(
                State.selected_opportunity_ids.length() > 0,
                "blue",
                "red",
            ),
            variant=rx.cond(State.prep_questions != "", "outline", "solid"),
        ),

        # --- Output Area ---
        rx.cond(
            State.prep_questions != "",
            rx.box(
                rx.flex(
                    rx.hstack(
                        rx.cond(
                            State.selected_opportunity_ids.length() > 0,
                            rx.badge("Interview Guide", color_scheme="blue", variant="solid"),
                            rx.badge("Battle Plan", color_scheme="red", variant="solid"),
                        ),
                        rx.text(
                            f"Generated: {State.prep_last_updated}",
                            color="gray",
                            size="1",
                        ),
                        spacing="3",
                        align="center",
                    ),
                    rx.button(
                        rx.icon("clipboard-copy", size=14),
                        "Copy",
                        on_click=State.copy_guide_to_clipboard,
                        size="1",
                        variant="soft",
                        color_scheme="gray",
                    ),
                    justify="between",
                    align="center",
                    margin_bottom="12px",
                ),
                rx.markdown(State.prep_questions),
                padding="20px",
                background_color="var(--gray-3)",
                border_radius="8px",
                width="100%",
                margin_top="4px",
            ),
        ),

        width="100%",
        max_width="900px",
        spacing="5",
        padding_top="20px",
    )
