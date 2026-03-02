import reflex as rx
from cont_synth.state import State, LedgerItem, PersonaBadge, QuoteItem, SolutionItem, ExperimentItem


# --- HELPER COMPONENTS ---
def render_persona_badge(badge: PersonaBadge):
    """Helper to render individual persona pills."""
    return rx.badge(badge.name, color_scheme=badge.color, variant="soft")


def render_quote(q: QuoteItem):
    """Renders a quote card for an individual evidence item inside the drawer."""
    return rx.box(
        rx.vstack(
            rx.flex(
                rx.badge(
                    q.persona_name,
                    color_scheme=q.persona_color,
                    variant="soft",
                    size="2",
                ),
                rx.icon_button(
                    rx.icon("trash", size=14),
                    size="1",
                    variant="ghost",
                    color_scheme="red",
                    on_click=lambda: State.delete_evidence(
                        State.selected_opportunity.opportunity_id, q.interview_id
                    ),
                ),
                justify="between",
                width="100%",
                align="center",
            ),
            rx.text(
                f'"{q.text}"', size="3", font_style="italic", color="var(--gray-12)"
            ),
            spacing="2",
        ),
        padding="16px",
        background_color="var(--blue-2)",
        border="1px solid var(--blue-6)",
        border_radius="8px",
        width="100%",
        flex_shrink="0",
    )


def render_solution(sol: SolutionItem):
    """Renders a sleek card for an individual solution idea with Edit/Branch controls."""
    return rx.box(
        rx.card(
            rx.vstack(
                rx.flex(
                    rx.flex(
                        rx.cond(
                            sol.indent_level > 0,
                            rx.icon(
                                "corner-down-right", size=14, color="var(--gray-8)"
                            ),
                            rx.fragment(),
                        ),
                        rx.text(
                            sol.name, weight="bold", size="3", color="var(--blue-11)"
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.flex(
                        rx.badge(
                            sol.status, color_scheme="blue", variant="soft", size="1"
                        ),
                        rx.icon_button(
                            rx.icon("flask-conical", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="purple",
                            title="Design an experiment for this solution",
                            on_click=lambda: State.open_add_experiment(sol.id, sol.name),
                        ),
                        rx.icon_button(
                            rx.icon("git-branch", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="blue",
                            on_click=lambda: State.set_target_parent(sol.id, sol.name),
                        ),
                        rx.icon_button(
                            rx.icon("pencil", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="gray",
                            on_click=lambda: State.start_edit_solution(sol),
                        ),
                        rx.icon_button(
                            rx.icon("trash", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="red",
                            on_click=lambda: State.delete_solution(sol.id),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    justify="between",
                    width="100%",
                ),
                rx.text(sol.description, size="2", color="gray"),
                spacing="2",
            ),
            size="2",
            width="100%",
            variant="surface",
            # --- THE MAGIC: Add a green left-border highlight if this card is the active parent! ---
            border_left=rx.cond(
                State.target_parent_id == sol.id,
                "4px solid var(--green-9)",
                "1px solid var(--gray-4)",
            ),
        ),
        width="100%",
        padding_left=f"calc({sol.indent_level} * 30px)",
    )


def _score_dot(item: LedgerItem, field: str, score: int) -> rx.Component:
    """A single clickable dot for the 1-5 score selector."""
    score_var = item.impact_score if field == "impact" else item.sat_gap_score
    is_filled = score_var >= score
    return rx.box(
        width="10px",
        height="10px",
        border_radius="50%",
        background_color=rx.cond(
            is_filled,
            rx.cond(field == "impact", "var(--blue-9)", "var(--violet-9)"),
            "var(--gray-4)",
        ),
        cursor="pointer",
        flex_shrink="0",
        on_click=lambda: State.update_opp_score(item.opportunity_id, field, str(score)),
        _hover={
            "background_color": rx.cond(
                field == "impact", "var(--blue-7)", "var(--violet-7)"
            )
        },
        transition="background-color 0.1s ease",
    )


def show_ledger_row(item: LedgerItem):
    """Renders a single opportunity as a card with Torres scoring and experiment status."""
    priority_color = rx.cond(
        item.priority_score >= 11, "green",
        rx.cond(item.priority_score >= 6, "amber",
            rx.cond(item.priority_score >= 1, "blue", "gray")),
    )

    return rx.box(
        rx.box(
        rx.vstack(
            # ── Row 1: badges + right-side status chips ──────────────────
            rx.flex(
                # Left: indent arrow + theme + tags
                rx.flex(
                    rx.cond(
                        item.indent_level > 0,
                        rx.icon("corner-down-right", size=13, color="var(--gray-7)"),
                        rx.fragment(),
                    ),
                    rx.cond(
                        item.is_target,
                        rx.badge(
                            rx.icon("crosshair", size=10),
                            "Target",
                            color_scheme="green", variant="solid", size="1",
                        ),
                        rx.fragment(),
                    ),
                    rx.badge(item.theme, color_scheme="gray", variant="solid", size="1"),
                    rx.cond(
                        item.is_cross_functional,
                        rx.badge("Cross-Persona", color_scheme="amber", variant="soft", size="1"),
                        rx.fragment(),
                    ),
                    spacing="2", align="center", flex="1",
                ),
                # Right: running experiments + priority score + target toggle
                rx.flex(
                    # Running experiments pill (only shown when > 0)
                    rx.cond(
                        item.running_experiments > 0,
                        rx.badge(
                            rx.icon("flask-conical", size=10),
                            f"{item.running_experiments} running",
                            color_scheme="orange", variant="soft", size="1",
                        ),
                        rx.fragment(),
                    ),
                    # Priority score badge
                    rx.badge(
                        f"P: {item.priority_score}",
                        color_scheme=priority_color,
                        variant=rx.cond(item.priority_score > 0, "soft", "outline"),
                        size="1",
                        title="Priority = Impact + Satisfaction Gap + Frequency (evidence count)",
                    ),
                    # Target toggle button
                    rx.icon_button(
                        rx.cond(
                            item.is_target,
                            rx.icon("crosshair", size=12),
                            rx.icon("crosshair", size=12),
                        ),
                        size="1",
                        variant=rx.cond(item.is_target, "solid", "ghost"),
                        color_scheme=rx.cond(item.is_target, "green", "gray"),
                        title=rx.cond(item.is_target, "Remove target designation", "Set as target opportunity"),
                        on_click=lambda: State.set_target_opportunity(item.opportunity_id),
                    ),
                    spacing="2", align="center", flex_shrink="0",
                ),
                justify="between", width="100%", align="center",
            ),
            # ── Row 2: Opportunity statement (hero text) ──────────────────
            rx.text(
                item.opportunity,
                weight="bold",
                size="4",
                line_height="1.4",
                cursor="pointer",
                on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
                _hover={"color": "var(--blue-11)"},
                transition="color 0.1s ease",
            ),
            # ── Row 3: Personas + quick metrics ──────────────────────────
            rx.flex(
                rx.flex(
                    rx.foreach(
                        item.personas_affected,
                        lambda b: rx.badge(b.name, color_scheme=b.color, variant="soft", size="1"),
                    ),
                    spacing="1", wrap="wrap",
                ),
                rx.flex(
                    rx.flex(
                        rx.icon("quote", size=11, color="var(--gray-8)"),
                        rx.text(f"{item.evidence.length()} quotes", size="1", color="var(--gray-8)"),
                        spacing="1", align="center",
                    ),
                    rx.text("·", size="1", color="var(--gray-6)"),
                    rx.flex(
                        rx.icon("lightbulb", size=11, color="var(--gray-8)"),
                        rx.text(f"{item.solutions.length()} solutions", size="1", color="var(--gray-8)"),
                        spacing="1", align="center",
                    ),
                    rx.text("·", size="1", color="var(--gray-6)"),
                    rx.text(
                        f"{item.days_old}d",
                        size="1",
                        weight="medium",
                        color=rx.cond(
                            item.status_color == "green", "var(--green-9)",
                            rx.cond(item.status_color == "yellow", "var(--amber-9)", "var(--red-9)"),
                        ),
                        title=item.status,
                    ),
                    spacing="2", align="center",
                ),
                justify="between", width="100%", align="center",
            ),
            # ── Row 4: Torres scoring ─────────────────────────────────────
            rx.flex(
                # Impact
                rx.flex(
                    rx.text("Impact", size="1", color="var(--gray-9)", weight="medium"),
                    _score_dot(item, "impact", 1),
                    _score_dot(item, "impact", 2),
                    _score_dot(item, "impact", 3),
                    _score_dot(item, "impact", 4),
                    _score_dot(item, "impact", 5),
                    spacing="1", align="center",
                ),
                rx.divider(orientation="vertical", size="1"),
                # Satisfaction gap
                rx.flex(
                    rx.text("Sat. Gap", size="1", color="var(--gray-9)", weight="medium"),
                    _score_dot(item, "sat_gap", 1),
                    _score_dot(item, "sat_gap", 2),
                    _score_dot(item, "sat_gap", 3),
                    _score_dot(item, "sat_gap", 4),
                    _score_dot(item, "sat_gap", 5),
                    spacing="1", align="center",
                ),
                rx.divider(orientation="vertical", size="1"),
                # Frequency note (auto-derived)
                rx.flex(
                    rx.text("Frequency", size="1", color="var(--gray-9)", weight="medium"),
                    rx.text(
                        f"{item.evidence.length()}/5 mentions",
                        size="1", color="var(--gray-10)",
                    ),
                    spacing="1", align="center",
                ),
                spacing="3", align="center",
            ),
            spacing="3",
            width="100%",
            align_items="start",
        ),
        padding="16px 16px 14px 20px",
        border_left=rx.cond(
            item.is_target,
            "4px solid var(--green-8)",
            rx.cond(
                item.status_color == "green", "4px solid var(--green-6)",
                rx.cond(item.status_color == "yellow", "4px solid var(--amber-6)", "4px solid var(--red-6)"),
            ),
        ),
        border_radius="8px",
        background_color=rx.cond(
            item.is_target, "var(--green-1)",
            rx.cond(item.indent_level > 0, "var(--gray-2)", "var(--gray-1)"),
        ),
        border="1px solid var(--gray-4)",
        width="100%",
        _hover={
            "background_color": rx.cond(item.is_target, "var(--green-2)", "var(--blue-1)"),
            "border_color": rx.cond(item.is_target, "var(--green-6)", "var(--blue-5)"),
        },
        transition="background-color 0.1s ease, border-color 0.1s ease",
    ),
    padding_left=f"calc({item.indent_level} * 28px)",
    width="100%",
    )


# --- OPPORTUNITY DRAWER SUBSECTIONS ---
def render_drawer_header() -> rx.Component:
    return rx.vstack(
        rx.flex(
            rx.badge(
                State.selected_opportunity.theme,
                color_scheme="gray",
                variant="solid",
                size="3",
            ),
            rx.drawer.close(
                rx.button(
                    rx.icon("x", size=18),
                    variant="ghost",
                    color_scheme="gray",
                    on_click=State.close_drawer,
                )
            ),
            justify="between",
            width="100%",
            align="center",
        ),
        rx.text(
            State.selected_opportunity.opportunity,
            weight="bold",
            size="6",
            margin_top="2",
            margin_bottom="4",
        ),
        width="100%",
    )


def render_primary_outcome_mapping() -> rx.Component:
    return rx.box(
        rx.text(
            "Primary Business Outcome:",
            size="1",
            weight="bold",
            color="gray",
            margin_bottom="8px",
        ),
        rx.cond(
            State.outcomes.length() == 0,
            rx.text(
                "No outcomes defined yet. Create one in the Global Ledger.",
                size="1",
                color="gray",
            ),
            rx.select(
                State.selectable_outcomes,
                placeholder="Select an Outcome...",
                value=State.selected_opp_outcome_name,
                on_change=State.set_primary_outcome,
                size="2",
                width="100%",
            ),
        ),
        padding="12px",
        background_color="var(--gray-3)",
        border_radius="6px",
        margin_bottom="6",
        width="100%",
    )


def render_evidence_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.flex(
                rx.cond(
                    State.selected_opportunity.evidence.length() > 0,
                    rx.foreach(State.selected_opportunity.evidence, render_quote),
                    rx.text("No evidence logged yet.", color="gray", size="2"),
                ),
                direction="column",
                spacing="4",
                width="100%",
                margin_top="8px",
            ),
            rx.box(
                rx.vstack(
                    rx.text(
                        "🔗 Map Missed Evidence", size="2", weight="bold", color="gray"
                    ),
                    rx.select(
                        State.interview_choices,
                        value=State.selected_interview_choice,
                        on_change=State.set_selected_interview_choice,
                        placeholder="Select Source Interview...",
                        width="100%",
                    ),
                    rx.text_area(
                        placeholder="Paste the exact verbatim quote here...",
                        value=State.manual_quote_text,
                        on_change=State.set_manual_quote_text,
                        width="100%",
                    ),
                    rx.button(
                        "Map Evidence",
                        on_click=lambda: State.add_real_evidence(
                            State.selected_opportunity.opportunity_id
                        ),
                        color_scheme="blue",
                        variant="soft",
                        width="100%",
                    ),
                    spacing="3",
                ),
                padding="16px",
                background_color="var(--gray-3)",
                border_radius="8px",
                margin_top="6",
                width="100%",
            ),
            width="100%",
            margin_top="4",
            padding_bottom="40px",
        ),
        value="evidence",
    )


def render_experiment_card(exp: ExperimentItem):
    signal_color = rx.cond(
        exp.signal == "Validated", "green",
        rx.cond(exp.signal == "Invalidated", "red", "gray")
    )
    return rx.card(
        rx.vstack(
            # Header row: badges + action buttons
            rx.flex(
                rx.flex(
                    rx.badge(exp.solution_name, color_scheme="blue", variant="soft", size="1"),
                    rx.badge(exp.method, color_scheme="purple", variant="soft", size="1"),
                    rx.badge(exp.status, color_scheme="orange", variant="soft", size="1"),
                    rx.badge(exp.signal, color_scheme=signal_color, variant="soft", size="1"),
                    spacing="1",
                    align="center",
                    wrap="wrap",
                ),
                rx.flex(
                    rx.cond(
                        exp.status != "Concluded",
                        rx.icon_button(rx.icon("pencil", size=14), size="1", variant="ghost",
                            color_scheme="gray",
                            on_click=lambda: State.start_edit_experiment(exp)),
                        rx.fragment(),
                    ),
                    rx.icon_button(rx.icon("trash", size=14), size="1", variant="ghost",
                        color_scheme="red", on_click=lambda: State.delete_experiment(exp.id)),
                    spacing="1",
                    align="center",
                ),
                justify="between", width="100%", align="center",
            ),
            # Experiment name + assumption
            rx.text(exp.name, weight="bold", size="3"),
            rx.text(f"Assumption: {exp.assumption}", size="2", color="gray"),
            # Status progression actions
            rx.flex(
                rx.cond(exp.status == "Draft",
                    rx.button("▶ Start Running", size="1", variant="soft",
                        on_click=lambda: State.update_experiment_status(exp.id, "Running")),
                    rx.fragment()),
                rx.cond(exp.status == "Running",
                    rx.button("✓ Conclude", size="1", variant="soft", color_scheme="orange",
                        on_click=lambda: State.update_experiment_status(exp.id, "Concluded")),
                    rx.fragment()),
                rx.cond(exp.status == "Concluded",
                    rx.flex(
                        rx.button("✅ Validated", size="1", variant="soft", color_scheme="green",
                            on_click=lambda: State.update_experiment_signal(exp.id, "Validated")),
                        rx.button("❌ Invalidated", size="1", variant="soft", color_scheme="red",
                            on_click=lambda: State.update_experiment_signal(exp.id, "Invalidated")),
                        spacing="2",
                    ),
                    rx.fragment()),
                spacing="2",
            ),
            # Suggestion button: appears after signal is set
            rx.cond(
                exp.signal != "Pending",
                rx.button(
                    rx.cond(exp.signal == "Validated", "→ Ship solution", "→ Discard solution"),
                    size="1",
                    variant="outline",
                    color_scheme=rx.cond(exp.signal == "Validated", "green", "red"),
                    on_click=lambda: State.apply_solution_outcome(exp.id),
                ),
                rx.fragment(),
            ),
            # Evidence notes: editable textarea when Concluded, read-only display otherwise
            rx.cond(
                exp.status == "Concluded",
                rx.vstack(
                    rx.text("Evidence / Learnings", size="1", weight="bold", color="gray"),
                    rx.text_area(
                        value=exp.evidence_notes,
                        placeholder="What did you observe? What did you learn?",
                        on_blur=lambda v: State.update_experiment_evidence(exp.id, v),
                        size="1",
                        width="100%",
                        rows="3",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.cond(
                    exp.evidence_notes != "",
                    rx.text(exp.evidence_notes, size="2", color="gray", style={"fontStyle": "italic"}),
                    rx.fragment(),
                ),
            ),
            spacing="2",
        ),
        size="2", width="100%", variant="surface",
    )


def render_experiments_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.flex(
                rx.cond(
                    State.selected_opportunity.experiments.length() > 0,
                    rx.foreach(State.selected_opportunity.experiments, render_experiment_card),
                    rx.text("No experiments designed yet.", color="gray", size="2"),
                ),
                direction="column",
                spacing="4",
                width="100%",
                margin_top="8px",
            ),
            rx.box(
                rx.vstack(
                    rx.text(
                        rx.cond(
                            State.editing_experiment_id != -1,
                            f"✏️ Editing: {State.new_experiment_name}",
                            rx.cond(
                                State.experiment_target_solution_name != "",
                                f"🧪 Testing: {State.experiment_target_solution_name}",
                                "🧪 Design New Experiment",
                            ),
                        ),
                        size="2",
                        weight="bold",
                        color=rx.cond(
                            State.editing_experiment_id != -1,
                            "var(--gray-11)",
                            rx.cond(
                                State.experiment_target_solution_name != "",
                                "var(--purple-11)",
                                "gray",
                            ),
                        ),
                    ),
                    rx.text("Target Solution", size="1", weight="bold", color="gray"),
                    rx.select(
                        State.solution_choices_for_experiment,
                        value=State.selected_solution_for_experiment,
                        on_change=State.set_selected_solution_for_experiment,
                        placeholder="Select a solution to test...",
                        width="100%",
                    ),
                    rx.input(
                        placeholder="Experiment name (e.g., Fake Door for Premium Export)",
                        value=State.new_experiment_name,
                        on_change=State.set_new_experiment_name,
                        width="100%",
                    ),
                    rx.text_area(
                        placeholder="What assumption are you testing? (e.g., Users will pay for faster exports)",
                        value=State.new_experiment_assumption,
                        on_change=State.set_new_experiment_assumption,
                        width="100%",
                    ),
                    rx.text("Method", size="1", weight="bold", color="gray"),
                    rx.select(
                        ["Prototype Interview", "Fake Door", "A/B Test", "Usability Test", "Survey", "Other"],
                        value=State.new_experiment_method,
                        on_change=State.set_new_experiment_method,
                        width="100%",
                    ),
                    rx.flex(
                        rx.button(
                            rx.cond(State.editing_experiment_id != -1, "Save Changes", "Design Experiment"),
                            on_click=lambda: State.add_experiment(
                                State.selected_opportunity.opportunity_id
                            ),
                            color_scheme="purple",
                            variant="solid",
                            flex="1",
                        ),
                        rx.cond(
                            (State.editing_experiment_id != -1) | (State.new_experiment_name != ""),
                            rx.button(
                                "Cancel",
                                on_click=State.cancel_experiment_form,
                                variant="soft",
                                color_scheme="gray",
                            ),
                            rx.fragment(),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    spacing="3",
                ),
                padding="16px",
                background_color="var(--gray-3)",
                border_radius="8px",
                margin_top="6",
                width="100%",
            ),
            width="100%",
            margin_top="4",
            padding_bottom="40px",
        ),
        value="experiments",
    )


def render_solutions_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.flex(
                rx.cond(
                    State.selected_opportunity.solutions.length() > 0,
                    rx.foreach(State.selected_opportunity.solutions, render_solution),
                    rx.text("No solutions brainstormed yet.", color="gray", size="2"),
                ),
                direction="column",
                spacing="4",
                width="100%",
                margin_top="8px",
            ),
            rx.box(
                rx.vstack(
                    rx.text(
                        rx.cond(
                            State.editing_solution_id != -1,
                            "✏️ Editing Solution",
                            rx.cond(
                                State.target_parent_id != -1,
                                f"🌿 Branching under: {State.target_parent_name}",
                                "💡 Ideate Top-Level Solution",
                            ),
                        ),
                        size="2",
                        weight="bold",
                        color=rx.cond(
                            State.target_parent_id != -1, "var(--green-11)", "gray"
                        ),
                    ),
                    rx.input(
                        placeholder="Solution Name",
                        value=State.new_solution_name,
                        on_change=State.set_new_solution_name,
                        width="100%",
                    ),
                    rx.text_area(
                        placeholder="Description",
                        value=State.new_solution_desc,
                        on_change=State.set_new_solution_desc,
                        width="100%",
                    ),
                    rx.flex(
                        rx.flex(
                            rx.button(
                                rx.cond(
                                    State.editing_solution_id != -1,
                                    "Update Idea",
                                    rx.cond(
                                        State.target_parent_id != -1,
                                        "Save Sub-Solution",
                                        "Save Idea",
                                    ),
                                ),
                                on_click=lambda: State.add_manual_solution(
                                    State.selected_opportunity.opportunity_id
                                ),
                                color_scheme="green",
                                variant="solid",
                            ),
                            rx.cond(
                                (State.editing_solution_id != -1)
                                | (State.target_parent_id != -1),
                                rx.button(
                                    "Cancel & Return to Top-Level",
                                    on_click=State.cancel_edit,
                                    color_scheme="gray",
                                    variant="soft",
                                ),
                                rx.fragment(),
                            ),
                            spacing="2",
                        ),
                        justify="between",
                        width="100%",
                    ),
                    spacing="3",
                ),
                padding="16px",
                background_color="var(--gray-3)",
                border_radius="8px",
                margin_top="6",
                width="100%",
            ),
            width="100%",
            margin_top="4",
            padding_bottom="40px",
        ),
        value="solutions",
    )


def render_drawer_tabs() -> rx.Component:
    return rx.tabs.root(
        rx.tabs.list(
            rx.tabs.trigger("Verbatim Evidence", value="evidence"),
            rx.tabs.trigger("Solutions Backlog", value="solutions"),
            rx.tabs.trigger("Experiments", value="experiments"),
            width="100%",
        ),
        render_evidence_tab(),
        render_solutions_tab(),
        render_experiments_tab(),
        value=State.active_drawer_tab,
        on_change=State.set_active_drawer_tab,
        margin_top="4",
        width="100%",
    )


# --- MAIN COMPONENTS ---
def opportunity_drawer() -> rx.Component:
    """The master workspace for a single opportunity."""
    return rx.drawer.root(
        rx.drawer.overlay(),
        rx.drawer.content(
            rx.cond(
                State.is_drawer_open,
                rx.box(
                    rx.vstack(
                        render_drawer_header(),
                        render_primary_outcome_mapping(),
                        render_drawer_tabs(),
                        width="100%",
                        padding="24px",
                    ),
                    height="100vh",
                    width="600px",
                    max_width="90vw",
                    bg="var(--gray-1)",
                    position="fixed",
                    top="0",
                    right="0",
                    overflow_y="auto",
                    box_shadow="-10px 0 30px rgba(0,0,0,0.1)",
                ),
                rx.fragment(),
            )
        ),
        direction="right",
        open=State.is_drawer_open,
        on_open_change=State.handle_drawer_change,
    )

def render_ledger() -> rx.Component:
    """The main view for the Global Ledger."""
    return rx.vstack(
        # --- NEW OUTCOME HEADER ---
        rx.flex(
            rx.box(
                rx.text("Opportunities List", weight="bold", size="6"),
                rx.text(
                    "Filter by business outcome to focus your Continuous Discovery efforts.",
                    color="gray",
                    size="3",
                ),
            ),
            rx.flex(
                rx.select(
                    State.outcome_names,
                    value=State.active_outcome_name,
                    on_change=State.change_outcome_filter,
                    size="3",
                    width="250px",
                ),
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("+ New Outcome", variant="soft", size="3")
                    ),
                    rx.dialog.content(
                        rx.dialog.title("Define Business Outcome"),
                        rx.dialog.description(
                            "What metric are we trying to move?", margin_bottom="8px"
                        ),
                        rx.input(
                            placeholder="e.g., Increase Q3 Retention",
                            value=State.new_outcome_name,
                            on_change=State.set_new_outcome_name,
                            margin_bottom="12px",
                        ),
                        rx.flex(
                            rx.dialog.close(
                                rx.button("Cancel", variant="soft", color_scheme="gray")
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Outcome",
                                    on_click=State.create_outcome,
                                    color_scheme="blue",
                                )
                            ),
                            spacing="3",
                            justify="end",
                        ),
                        max_width="450px",
                    ),
                ),
                spacing="3",
                align="center",
            ),
            justify="between",
            width="100%",
            margin_bottom="10px",
            align="center",
        ),
        rx.divider(),
        # --- Action Bar & Opportunity Form Dialog ---
        rx.flex(
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button(
                        "+ New Opportunity",
                        size="2",
                        color_scheme="blue",
                        variant="soft",
                        on_click=State.open_opp_dialog,
                    )
                ),
                rx.dialog.content(
                    rx.dialog.title(
                        rx.cond(
                            State.editing_opp_id != -1,
                            "Edit Opportunity",
                            "Create Manual Opportunity",
                        )
                    ),
                    rx.dialog.description(
                        "Manually add or update an opportunity.", margin_bottom="8px"
                    ),
                    rx.vstack(
                        rx.text("Parent Opportunity", size="2", weight="bold"),
                        rx.select(
                            State.parent_opp_choices,
                            value=State.manual_opp_parent_id,
                            on_change=State.set_manual_opp_parent_id,
                            width="100%",
                        ),
                        rx.text("Theme / Category", size="2", weight="bold"),
                        rx.input(
                            placeholder="e.g., Usability, Pricing...",
                            value=State.manual_opp_theme,
                            on_change=State.set_manual_opp_theme,
                            width="100%",
                        ),
                        rx.text(
                            "Opportunity Statement",
                            size="2",
                            weight="bold",
                            margin_top="2",
                        ),
                        rx.text_area(
                            placeholder="I need a way to...",
                            value=State.manual_opp_statement,
                            on_change=State.set_manual_opp_statement,
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                        margin_bottom="12px",
                    ),
                    rx.flex(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                            on_click=State.close_opp_dialog,
                        ),
                        rx.button(
                            "Save Opportunity",
                            on_click=State.save_manual_opportunity,
                            color_scheme="blue",
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    max_width="500px",
                ),
                open=State.is_opp_dialog_open,
                on_open_change=State.handle_opp_dialog_change,
            ),
            spacing="3",
            width="100%",
            justify="start",
            margin_bottom="4",
        ),
        rx.cond(
            State.ledger_data.length() == 0,
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=36, color="var(--gray-7)"),
                    rx.text("No opportunities found.", weight="medium", color="gray"),
                    rx.text(
                        "Create one with the button above, or run a synthesis from an interview.",
                        size="2", color="gray", text_align="center",
                    ),
                    spacing="2", align="center",
                ),
                padding_y="80px",
                width="100%",
            ),
            rx.vstack(
                rx.foreach(State.ledger_data, show_ledger_row),
                spacing="2",
                width="100%",
            ),
        ),
        width="100%",
        max_width="1400px",
        spacing="4",
        padding_top="20px",
    )
