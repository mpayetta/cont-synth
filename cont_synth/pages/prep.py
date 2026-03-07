import reflex as rx
from cont_synth.state import State
from cont_synth.state.core import PrepOppItem, PrepExperimentItem, PrepGuideItem


def _render_prep_opp_table_row(opp: PrepOppItem) -> rx.Component:
    """One compact table row for an opportunity: checkbox | theme | statement | personas."""
    return rx.table.row(
        rx.table.cell(
            rx.checkbox(
                checked=opp.selected,
                on_change=lambda _: State.toggle_prep_opportunity(opp.id),
                color_scheme="blue",
                size="2",
            ),
            padding="0 8px",
            vertical_align="middle",
        ),
        rx.table.cell(
            rx.badge(opp.theme, color_scheme="gray", variant="soft", size="1"),
            vertical_align="middle",
            white_space="nowrap",
        ),
        rx.table.cell(
            rx.text(opp.statement, size="2", color="var(--gray-12)"),
            vertical_align="middle",
        ),
        rx.table.cell(
            rx.cond(
                opp.personas.length() > 0,
                rx.flex(
                    rx.foreach(
                        opp.personas,
                        lambda p: rx.badge(p, color_scheme="blue", variant="soft", size="1"),
                    ),
                    gap="4px",
                    flex_wrap="wrap",
                ),
                rx.text("—", size="2", color="var(--gray-9)"),
            ),
            vertical_align="middle",
        ),
        _hover={"background_color": rx.cond(opp.selected, "var(--blue-3)", "var(--gray-2)")},
        background_color=rx.cond(opp.selected, "var(--blue-2)", "transparent"),
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
                    rx.text(exp.solution_name, size="1", color="var(--gray-12)", weight="medium"),
                    rx.text("·", size="1", color="var(--gray-12)"),
                    rx.text(exp.experiment_name, size="1", color="var(--gray-12)"),
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


def _render_coach_pregame_brief() -> rx.Component:
    """Purple-accented panel showing last interview score and stop-doing habits."""
    return rx.cond(
        State.last_interview_score > 0,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("graduation-cap", size=16, color="#6E56CF"),
                    rx.text(
                        "Coach's Pre-Game Brief",
                        weight="bold",
                        size="3",
                        color="#6E56CF",
                    ),
                    rx.spacer(),
                    rx.badge(
                        f"Last score: {State.last_interview_score}/10",
                        color_scheme="violet",
                        variant="soft",
                        size="1",
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                rx.text(
                    "Based on your last interview, avoid these habits:",
                    size="2",
                    color="var(--gray-11)",
                ),
                rx.cond(
                    State.last_stop_doing.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            State.last_stop_doing,
                            lambda item: rx.hstack(
                                rx.text("•", size="2", color="#6E56CF", flex_shrink="0"),
                                rx.text(item, size="2", color="var(--gray-12)"),
                                spacing="2",
                                align="start",
                            ),
                        ),
                        spacing="1",
                        align_items="start",
                        width="100%",
                    ),
                    rx.text(
                        "No specific stop-doing items from your last session.",
                        size="2",
                        color="var(--gray-10)",
                        style={"font_style": "italic"},
                    ),
                ),
                spacing="3",
                align_items="start",
                width="100%",
            ),
            padding="16px 20px",
            border_radius="8px",
            background_color="rgba(131, 56, 236, 0.06)",
            border="1px solid rgba(131, 56, 236, 0.25)",
            width="100%",
        ),
    )


def _render_guide_table_row(guide: PrepGuideItem) -> rx.Component:
    """One row in the guide history table."""
    return rx.table.row(
        rx.table.cell(
            rx.text(guide.created_at, size="2", color="var(--gray-11)"),
        ),
        rx.table.cell(
            rx.cond(
                guide.target_persona != "",
                rx.badge(guide.target_persona, color_scheme="gray", variant="soft", size="1"),
                rx.text("—", size="2", color="var(--gray-9)"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                guide.used_coach_feedback,
                rx.badge(
                    rx.hstack(
                        rx.icon("graduation-cap", size=10),
                        rx.text("Applied", size="1"),
                        spacing="1",
                        align="center",
                    ),
                    color_scheme="violet",
                    variant="soft",
                    size="1",
                ),
                rx.text("—", size="2", color="var(--gray-9)"),
            ),
        ),
        rx.table.cell(
            rx.button(
                rx.icon("panel-right-open", size=13),
                "Open",
                on_click=State.open_guide_drawer(guide.id),
                size="1",
                variant="soft",
                color_scheme="gray",
            ),
        ),
        _hover={"background_color": "var(--gray-2)"},
    )


def _guide_drawer() -> rx.Component:
    """Right-side slide-over drawer showing full input context + output for a selected guide."""
    g = State.selected_guide_item
    return rx.drawer.root(
        rx.drawer.overlay(),
        rx.drawer.content(
            rx.cond(
                State.guide_drawer_open,
                rx.box(
                    rx.vstack(
                        # --- Drawer header ---
                        rx.flex(
                            rx.vstack(
                                rx.hstack(
                                    rx.badge("Interview Guide", color_scheme="blue", variant="solid", size="1"),
                                    rx.cond(
                                        g.used_coach_feedback,
                                        rx.badge(
                                            rx.hstack(
                                                rx.icon("graduation-cap", size=10),
                                                rx.text("Coach applied", size="1"),
                                                spacing="1",
                                                align="center",
                                            ),
                                            color_scheme="violet",
                                            variant="soft",
                                            size="1",
                                        ),
                                    ),
                                    spacing="2",
                                ),
                                rx.text(g.created_at, size="2", color="var(--gray-10)"),
                                spacing="1",
                                align_items="start",
                            ),
                            rx.spacer(),
                            rx.icon_button(
                                rx.icon("x", size=16),
                                variant="ghost",
                                color_scheme="gray",
                                on_click=State.close_guide_drawer,
                            ),
                            align="center",
                            spacing="3",
                            width="100%",
                        ),
                        rx.divider(),

                        # --- INPUT SECTION ---
                        rx.vstack(
                            rx.text("Input Context", weight="bold", size="3", color="var(--gray-12)"),
                            rx.text(
                                "Everything the AI received when generating this guide.",
                                size="2",
                                color="var(--gray-10)",
                            ),

                            # Persona
                            rx.cond(
                                g.target_persona != "",
                                rx.vstack(
                                    rx.text("Persona", size="1", weight="medium", color="var(--gray-10)"),
                                    rx.badge(g.target_persona, color_scheme="blue", variant="soft", size="2"),
                                    spacing="1",
                                    align_items="start",
                                ),
                            ),

                            # Opportunities
                            rx.cond(
                                g.input_opportunities.length() > 0,
                                rx.vstack(
                                    rx.text("Opportunities", size="1", weight="medium", color="var(--gray-10)"),
                                    rx.vstack(
                                        rx.foreach(
                                            g.input_opportunities,
                                            lambda opp: rx.hstack(
                                                rx.cond(
                                                    opp["theme"] != "",
                                                    rx.badge(opp["theme"], color_scheme="gray", variant="soft", size="1"),
                                                ),
                                                rx.text(opp["statement"], size="2", color="var(--gray-12)"),
                                                spacing="2",
                                                align="start",
                                                flex_wrap="wrap",
                                            ),
                                        ),
                                        spacing="2",
                                        align_items="start",
                                        width="100%",
                                    ),
                                    spacing="1",
                                    align_items="start",
                                    width="100%",
                                ),
                            ),

                            # Extra context
                            rx.cond(
                                g.input_extra_context != "",
                                rx.vstack(
                                    rx.text("Additional context", size="1", weight="medium", color="var(--gray-10)"),
                                    rx.box(
                                        rx.text(g.input_extra_context, size="2", color="var(--gray-12)"),
                                        padding="10px 12px",
                                        border_radius="6px",
                                        background_color="var(--gray-3)",
                                        border="1px solid var(--gray-5)",
                                        width="100%",
                                    ),
                                    spacing="1",
                                    align_items="start",
                                    width="100%",
                                ),
                            ),

                            # Coach feedback used
                            rx.cond(
                                g.used_coach_feedback,
                                rx.vstack(
                                    rx.text("Coach feedback injected", size="1", weight="medium", color="var(--gray-10)"),
                                    rx.box(
                                        rx.vstack(
                                            rx.hstack(
                                                rx.icon("graduation-cap", size=13, color="#6E56CF"),
                                                rx.text(
                                                    f"Last score: {g.input_coach_score}/10",
                                                    size="2",
                                                    color="var(--gray-12)",
                                                    weight="medium",
                                                ),
                                                spacing="2",
                                                align="center",
                                            ),
                                            rx.cond(
                                                g.input_stop_doing.length() > 0,
                                                rx.vstack(
                                                    rx.text("Stop doing:", size="1", color="var(--gray-10)"),
                                                    rx.foreach(
                                                        g.input_stop_doing,
                                                        lambda item: rx.hstack(
                                                            rx.text("•", size="2", color="#6E56CF", flex_shrink="0"),
                                                            rx.text(item, size="2", color="var(--gray-12)"),
                                                            spacing="2",
                                                            align="start",
                                                        ),
                                                    ),
                                                    spacing="1",
                                                    align_items="start",
                                                    width="100%",
                                                ),
                                            ),
                                            spacing="2",
                                            align_items="start",
                                            width="100%",
                                        ),
                                        padding="10px 12px",
                                        border_radius="6px",
                                        background_color="rgba(131, 56, 236, 0.06)",
                                        border="1px solid rgba(131, 56, 236, 0.2)",
                                        width="100%",
                                    ),
                                    spacing="1",
                                    align_items="start",
                                    width="100%",
                                ),
                            ),

                            spacing="4",
                            align_items="start",
                            width="100%",
                            padding="16px",
                            background_color="var(--gray-2)",
                            border_radius="8px",
                            border="1px solid var(--gray-4)",
                        ),

                        rx.divider(),

                        # --- OUTPUT SECTION ---
                        rx.vstack(
                            rx.text("Generated Guide", weight="bold", size="3", color="var(--gray-12)"),
                            rx.markdown(g.content),
                            spacing="3",
                            align_items="start",
                            width="100%",
                        ),

                        spacing="4",
                        padding="24px",
                        width="100%",
                    ),
                    height="100vh",
                    width="580px",
                    max_width="90vw",
                    bg="var(--gray-1)",
                    position="fixed",
                    top="0",
                    right="0",
                    overflow_y="auto",
                    box_shadow="-10px 0 30px rgba(0,0,0,0.15)",
                ),
                rx.fragment(),
            ),
        ),
        direction="right",
        open=State.guide_drawer_open,
        on_open_change=State.close_guide_drawer,
        dismissible=True,
    )


def render_prep() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.text("Pre-Meeting Prep", weight="bold", size="6"),
            rx.text(
                "Generate interview guides tailored to the opportunities you want to explore, and review your past guides.",
                color="gray",
                size="3",
            ),
            spacing="1",
            margin_bottom="4px",
        ),
        rx.divider(),
        rx.tabs.root(
        # --- Tab List ---
        rx.tabs.list(
            rx.tabs.trigger("Create Guide", value="create"),
            rx.tabs.trigger("Guide History", value="history"),
            size="2",
        ),

        # ── TAB 1: CREATE GUIDE ──────────────────────────────────────────────
        rx.tabs.content(
            rx.vstack(
                # Coach Pre-Game Brief
                _render_coach_pregame_brief(),

                # Persona Selector (moved here, right after the brief)
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
                        color="var(--gray-12)",
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
                ),

                # Opportunity Selector (compact table)
                rx.vstack(
                    rx.hstack(
                        rx.text("Opportunities to explore", weight="medium", size="3"),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(
                        "Check the opportunities you want to probe in this interview. The guide will include discovery questions for each.",
                        size="2",
                        color="var(--gray-12)",
                    ),
                    rx.cond(
                        State.prep_opportunities.length() > 0,
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("", width="40px"),
                                    rx.table.column_header_cell("Theme"),
                                    rx.table.column_header_cell("Opportunity"),
                                    rx.table.column_header_cell("Personas"),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(State.prep_opportunities, _render_prep_opp_table_row),
                            ),
                            variant="surface",
                            size="1",
                            width="100%",
                        ),
                        rx.box(
                            rx.text(
                                "No opportunities found. Add some in the Opportunity Ledger first.",
                                size="2",
                                color="var(--gray-12)",
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

                # Experiment Assumptions Selector
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
                            color="var(--gray-12)",
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

                # Extra Context
                rx.vstack(
                    rx.hstack(
                        rx.text("Additional context", weight="medium", size="3"),
                        rx.badge("Optional", color_scheme="gray", variant="soft", size="1"),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(
                        "Describe the goal of this interview, topics to cover, or any background the LLM should know. Useful when the conversation isn't tied to specific opportunities.",
                        size="2",
                        color="var(--gray-12)",
                    ),
                    rx.text_area(
                        placeholder="e.g. This is an onboarding call with a new enterprise customer. I want to understand their workflow before any product training happens.",
                        value=State.prep_extra_context,
                        on_change=State.set_prep_extra_context,
                        rows="4",
                        resize="vertical",
                        width="100%",
                    ),
                    spacing="2",
                    align_items="start",
                    width="100%",
                    padding_top="4px",
                ),

                # Coach feedback toggle + Generate button
                rx.vstack(
                    rx.cond(
                        State.last_interview_score > 0,
                        rx.hstack(
                            rx.switch(
                                checked=State.apply_coach_feedback,
                                on_change=State.set_apply_coach_feedback,
                                color_scheme="violet",
                                size="2",
                            ),
                            rx.text(
                                "Apply past coaching feedback to script",
                                size="2",
                                color="var(--gray-11)",
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                    rx.hstack(
                        rx.spacer(),
                        rx.button(
                            rx.cond(
                                State.prep_questions != "",
                                "Regenerate Interview Guide",
                                "Generate Interview Guide",
                            ),
                            on_click=State.generate_hostile_questions,
                            loading=State.is_prepping,
                            disabled=State.is_viewer,
                            size="3",
                            color_scheme="blue",
                            variant=rx.cond(State.prep_questions != "", "outline", "solid"),
                        ),
                        width="100%",
                    ),
                    spacing="3",
                    align_items="start",
                    width="100%",
                ),

                # Output Area
                rx.cond(
                    State.prep_questions != "",
                    rx.box(
                        rx.flex(
                            rx.hstack(
                                rx.badge("Interview Guide", color_scheme="blue", variant="solid"),
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
                        rx.box(
                            rx.markdown(State.prep_questions),
                            overflow_x="auto",
                            width="100%",
                        ),
                        padding="20px",
                        background_color="var(--gray-3)",
                        border_radius="8px",
                        width="100%",
                        overflow_x="auto",
                        margin_top="4px",
                    ),
                ),

                width="100%",
                spacing="5",
            ),
            value="create",
            padding_top="16px",
        ),

        # ── TAB 2: GUIDE HISTORY ─────────────────────────────────────────────
        rx.tabs.content(
            rx.vstack(
                rx.cond(
                    State.guide_history.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Date"),
                                rx.table.column_header_cell("Persona"),
                                rx.table.column_header_cell("Coach"),
                                rx.table.column_header_cell(""),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(State.guide_history, _render_guide_table_row),
                        ),
                        variant="surface",
                        width="100%",
                    ),
                    rx.box(
                        rx.text(
                            "No guides generated yet. Create your first guide in the Create Guide tab.",
                            size="2",
                            color="var(--gray-10)",
                            style={"font_style": "italic"},
                        ),
                        padding="20px",
                        background_color="var(--gray-2)",
                        border_radius="8px",
                        width="100%",
                    ),
                ),
                width="100%",
                spacing="5",
            ),
            value="history",
            padding_top="16px",
        ),

        # Guide detail drawer (rendered at root level so it overlays the whole page)
        _guide_drawer(),

        default_value="create",
        width="100%",
        ),
        width="100%",
        max_width="900px",
        spacing="4",
        padding_top="20px",
        align_items="stretch",
    )
