import reflex as rx
from cont_synth.state import State, OppDetailSolution, ExperimentItem, QuoteItem
from cont_synth.pages.ledger import _merge_dialog
from cont_synth.pages.ui import combo_box


# --- SCORING HELPERS ---

def _info_label_detail(text, explanation: str) -> rx.Component:
    """A label + clickable ? icon that opens a popover with an explanation."""
    return rx.flex(
        rx.text(text, size="2", color="var(--gray-12)", weight="medium"),
        rx.popover.root(
            rx.popover.trigger(
                rx.icon(
                    "circle-help",
                    size=14,
                    color="var(--gray-12)",
                    cursor="pointer",
                    _hover={"color": "var(--gray-12)"},
                ),
            ),
            rx.popover.content(
                rx.text(explanation, size="2"),
                max_width="280px",
                side="top",
            ),
        ),
        spacing="1",
        align="center",
    )


def _score_dot_detail(field: str, score: int) -> rx.Component:
    """A single clickable dot for scoring on the opportunity detail page."""
    item = State.selected_opportunity
    score_var = item.impact_score if field == "impact" else item.sat_gap_score
    is_filled = score_var >= score
    return rx.box(
        width="12px",
        height="12px",
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


# --- EVIDENCE PANEL HELPERS ---

def render_detail_quote(q: QuoteItem) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.flex(
                rx.badge(q.persona_name, color_scheme=q.persona_color, variant="soft", size="2"),
                rx.cond(
                    ~State.is_viewer,
                    rx.flex(
                        rx.icon_button(
                            rx.icon("arrow-right-left", size=14),
                            size="1", variant="ghost", color_scheme="blue",
                            title="Reassign to another opportunity",
                            on_click=State.open_reassign_evidence_dialog(
                                q.interview_id, State.selected_opportunity.opportunity_id
                            ),
                        ),
                        rx.alert_dialog.root(
                            rx.alert_dialog.trigger(
                                rx.icon_button(
                                    rx.icon("trash", size=14),
                                    size="1", variant="ghost", color_scheme="red",
                                ),
                            ),
                            rx.alert_dialog.content(
                                rx.alert_dialog.title("Remove Evidence"),
                                rx.alert_dialog.description(
                                    f'Remove the quote from {q.persona_name}? This unlinks the interview from this opportunity but does not delete the interview itself.',
                                    size="2",
                                ),
                                rx.flex(
                                    rx.alert_dialog.cancel(
                                        rx.button("Cancel", variant="soft", color_scheme="gray"),
                                    ),
                                    rx.alert_dialog.action(
                                        rx.button(
                                            "Remove",
                                            color_scheme="red",
                                            on_click=lambda: State.delete_evidence(
                                                State.selected_opportunity.opportunity_id, q.interview_id
                                            ),
                                        ),
                                    ),
                                    spacing="3", justify="end", margin_top="16px",
                                ),
                                max_width="420px",
                            ),
                        ),
                        spacing="1",
                        align="center",
                    ),
                ),  # end rx.cond(~is_viewer)
                justify="between", width="100%", align="center",
            ),
            # Quote text is the clickable area for opening the transcript drawer
            rx.box(
                rx.hstack(
                    rx.icon("external-link", size=12, color="var(--blue-8)"),
                    rx.text(f'"{q.text}"', size="3", font_style="italic", color="var(--gray-12)"),
                    spacing="2",
                    align="start",
                ),
                on_click=State.open_transcript_drawer(q.interview_id, q.text),
                cursor="pointer",
                border_radius="4px",
                padding="4px",
                margin="-4px",
                _hover={"background_color": "var(--blue-3)"},
                width="100%",
            ),
            spacing="2",
        ),
        padding="16px",
        background_color="var(--blue-2)",
        border="1px solid var(--blue-6)",
        border_radius="8px",
        width="100%",
    )


def render_evidence_panel() -> rx.Component:
    return rx.vstack(
        rx.cond(
            State.selected_opportunity.evidence.length() > 0,
            rx.vstack(
                rx.foreach(State.selected_opportunity.evidence, render_detail_quote),
                spacing="3", width="100%",
            ),
            rx.text("No evidence logged yet.", color="gray", size="2"),
        ),
        # Map missed evidence form — hidden for viewers
        rx.cond(
            ~State.is_viewer,
            rx.box(
                rx.vstack(
                    rx.text("🔗 Map Missed Evidence", size="2", weight="bold", color="gray"),
                    rx.select(
                        State.available_interview_choices,
                        value=State.selected_interview_choice,
                        on_change=State.set_selected_interview_choice,
                        placeholder="Select Source Interview...",
                        width="100%",
                        size="1",
                    ),
                    rx.button(
                        rx.icon("file-text", size=14),
                        "Open in Transcript",
                        on_click=State.open_transcript_for_selection(
                            State.selected_opportunity.opportunity_id
                        ),
                        color_scheme="blue", variant="soft", size="1", width="100%",
                    ),
                    spacing="2",
                ),
                padding="12px",
                background_color="var(--gray-3)",
                border_radius="8px",
                margin_top="4",
                width="100%",
            ),
        ),
        spacing="4",
        width="100%",
        align_items="start",
    )


# --- EXPERIMENT HELPERS ---

def render_detail_experiment(exp: ExperimentItem) -> rx.Component:
    signal_color = rx.cond(
        exp.signal == "Validated", "green",
        rx.cond(exp.signal == "Invalidated", "red", "gray"),
    )
    return rx.box(
        rx.vstack(
            rx.flex(
                rx.flex(
                    rx.icon("flask-conical", size=12, color="var(--purple-9)"),
                    rx.text(exp.name, weight="medium", size="2"),
                    spacing="2", align="center",
                ),
                rx.flex(
                    rx.badge(exp.method, color_scheme="purple", variant="soft", size="1"),
                    rx.badge(exp.status, color_scheme="orange", variant="soft", size="1"),
                    rx.badge(exp.signal, color_scheme=signal_color, variant="soft", size="1"),
                    # Edit/delete — hidden for viewers
                    rx.cond(
                        ~State.is_viewer,
                        rx.flex(
                            rx.cond(
                                exp.status != "Concluded",
                                rx.icon_button(
                                    rx.icon("pencil", size=12),
                                    size="1", variant="ghost", color_scheme="gray",
                                    on_click=lambda: State.start_edit_experiment(exp),
                                ),
                                rx.fragment(),
                            ),
                            rx.alert_dialog.root(
                                rx.alert_dialog.trigger(
                                    rx.icon_button(
                                        rx.icon("trash", size=12),
                                        size="1", variant="ghost", color_scheme="red",
                                    ),
                                ),
                                rx.alert_dialog.content(
                                    rx.alert_dialog.title("Delete Experiment"),
                                    rx.alert_dialog.description(
                                        f'Delete the experiment "{exp.name}"? All progress and results will be permanently lost.',
                                        size="2",
                                    ),
                                    rx.flex(
                                        rx.alert_dialog.cancel(
                                            rx.button("Cancel", variant="soft", color_scheme="gray"),
                                        ),
                                        rx.alert_dialog.action(
                                            rx.button(
                                                "Delete Experiment",
                                                color_scheme="red",
                                                on_click=lambda: State.delete_experiment(exp.id),
                                            ),
                                        ),
                                        spacing="3", justify="end", margin_top="16px",
                                    ),
                                    max_width="420px",
                                ),
                            ),
                            spacing="1", align="center",
                        ),
                    ),
                    spacing="1", align="center",
                ),
                justify="between", width="100%", align="center",
            ),
            rx.text(
                f'Assumption: "{exp.assumption}"',
                size="1", color="gray", font_style="italic",
            ),
            rx.cond(
                exp.description != "",
                rx.text(f"Description: {exp.description}", size="1", color="gray"),
                rx.fragment(),
            ),
            rx.cond(
                exp.success_metric != "",
                rx.hstack(
                    rx.icon("chart-line", size=12, color="var(--green-9)"),
                    rx.text(exp.success_metric, size="1", color="var(--green-11)", weight="medium"),
                    spacing="1", align="center",
                ),
                rx.fragment(),
            ),
            # Progress action buttons — hidden for viewers
            rx.cond(
                ~State.is_viewer,
                rx.flex(
                    rx.cond(
                        exp.status == "Draft",
                        rx.button(
                            "▶ Start Running", size="1", variant="soft",
                            on_click=lambda: State.update_experiment_status(exp.id, "Running"),
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        exp.status == "Running",
                        rx.button(
                            "✓ Conclude", size="1", variant="soft", color_scheme="orange",
                            on_click=lambda: State.update_experiment_status(exp.id, "Concluded"),
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        exp.status == "Concluded",
                        rx.cond(
                            exp.signal == "Pending",
                            rx.flex(
                                rx.button(
                                    "✅ Validated", size="1", variant="soft", color_scheme="green",
                                    on_click=lambda: State.update_experiment_signal(exp.id, "Validated"),
                                ),
                                rx.button(
                                    "❌ Invalidated", size="1", variant="soft", color_scheme="red",
                                    on_click=lambda: State.update_experiment_signal(exp.id, "Invalidated"),
                                ),
                                spacing="2",
                            ),
                            rx.fragment(),
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
            ),
            # Suggestion button — hidden for viewers
            rx.cond(
                (~State.is_viewer) & (exp.signal != "Pending"),
                rx.button(
                    rx.cond(exp.signal == "Validated", "→ Ship solution", "→ Discard solution"),
                    size="1",
                    variant="outline",
                    color_scheme=rx.cond(exp.signal == "Validated", "green", "red"),
                    on_click=lambda: State.apply_solution_outcome(exp.id),
                ),
                rx.fragment(),
            ),
            # Evidence notes: editable textarea when Concluded (read-only for viewers)
            rx.cond(
                exp.status == "Concluded",
                rx.vstack(
                    rx.text("Evidence / Learnings", size="1", weight="bold", color="gray"),
                    rx.cond(
                        ~State.is_viewer,
                        rx.text_area(
                            default_value=exp.evidence_notes,
                            placeholder="What did you observe? What did you learn?",
                            on_blur=lambda v: State.update_experiment_evidence(exp.id, v),
                            size="1",
                            width="100%",
                            rows="3",
                        ),
                        rx.text(exp.evidence_notes, size="1", color="gray", font_style="italic"),
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.cond(
                    exp.evidence_notes != "",
                    rx.text(exp.evidence_notes, size="1", color="gray", font_style="italic"),
                    rx.fragment(),
                ),
            ),
            spacing="2", width="100%",
        ),
        padding="10px",
        background_color="var(--purple-2)",
        border_radius="6px",
        border="1px solid var(--purple-4)",
        width="100%",
    )


def render_inline_experiment_form() -> rx.Component:
    """The inline experiment design form that appears inside a solution card."""
    return rx.box(
        rx.vstack(
            rx.input(
                placeholder="Experiment name (e.g., Fake Door for Premium Export)",
                default_value=State.new_experiment_name,
                on_blur=State.set_new_experiment_name,
                width="100%", size="1",
            ),
            rx.text("Assumption", size="1", weight="bold", color="gray"),
            rx.text_area(
                placeholder="What assumption are you testing? (e.g., Users will pay for faster exports)",
                default_value=State.new_experiment_assumption,
                on_blur=State.set_new_experiment_assumption,
                width="100%", rows="2",
            ),
            rx.text("Description", size="1", weight="bold", color="gray"),
            rx.text_area(
                placeholder="What will you do? How will you run it?",
                default_value=State.new_experiment_description,
                on_blur=State.set_new_experiment_description,
                width="100%", rows="2",
            ),
            rx.text("Success Metric", size="1", weight="bold", color="gray"),
            rx.input(
                placeholder="How will you know it worked? (e.g., ≥30% click-through on CTA)",
                default_value=State.new_experiment_success_metric,
                on_blur=State.set_new_experiment_success_metric,
                width="100%", size="1",
            ),
            rx.text("Method", size="1", weight="bold", color="gray"),
            rx.select(
                ["Prototype Interview", "Fake Door", "A/B Test", "Usability Test", "Survey", "Other"],
                value=State.new_experiment_method,
                on_change=State.set_new_experiment_method,
                width="100%", size="1",
            ),
            rx.cond(
                State.new_experiment_method == "Other",
                rx.input(
                    placeholder="Describe the experiment type...",
                    default_value=State.new_experiment_method_other,
                    on_blur=State.set_new_experiment_method_other,
                    width="100%", size="1",
                ),
                rx.fragment(),
            ),
            rx.flex(
                rx.button(
                    rx.cond(State.editing_experiment_id != -1, "Save Changes", "Save Experiment"),
                    on_click=lambda: State.add_experiment(
                        State.selected_opportunity.opportunity_id
                    ),
                    color_scheme="purple", variant="solid", size="1",
                ),
                rx.button(
                    "Cancel",
                    on_click=State.cancel_experiment_form,
                    color_scheme="gray", variant="soft", size="1",
                ),
                spacing="2",
            ),
            spacing="2", width="100%",
        ),
        padding="12px",
        background_color="var(--purple-3)",
        border_radius="6px",
        border="1px solid var(--purple-6)",
        width="100%",
    )


# --- SOLUTION DETAIL CARD ---

def render_solution_detail_card(sol: OppDetailSolution) -> rx.Component:
    status_color = rx.cond(
        sol.status == "Shipped", "green",
        rx.cond(
            sol.status == "Testing", "orange",
            rx.cond(sol.status == "Discarded", "red", "blue"),
        ),
    )
    return rx.box(
        rx.card(
            rx.vstack(
                # Header row: name + controls
                rx.flex(
                    rx.flex(
                        rx.cond(
                            sol.indent_level > 0,
                            rx.icon("corner-down-right", size=14, color="var(--gray-12)"),
                            rx.fragment(),
                        ),
                        rx.text(sol.name, weight="bold", size="4", color="var(--blue-11)"),
                        spacing="2", align="center",
                    ),
                    rx.flex(
                        rx.badge(sol.status, color_scheme=status_color, variant="soft", size="1"),
                        rx.cond(
                            ~State.is_viewer,
                            rx.flex(
                                rx.icon_button(
                                    rx.icon("flask-conical", size=14),
                                    size="1", variant="ghost", color_scheme="purple",
                                    title="Design an experiment",
                                    on_click=lambda: State.open_add_experiment(sol.id, sol.name),
                                ),
                                rx.icon_button(
                                    rx.icon("git-branch", size=14),
                                    size="1", variant="ghost", color_scheme="blue",
                                    title="Add sub-solution",
                                    on_click=lambda: State.set_target_parent(sol.id, sol.name),
                                ),
                                rx.icon_button(
                                    rx.icon("pencil", size=14),
                                    size="1", variant="ghost", color_scheme="gray",
                                    on_click=lambda: State.start_edit_solution_from_detail(
                                        sol.id, sol.name, sol.description, sol.status
                                    ),
                                ),
                                rx.alert_dialog.root(
                                    rx.alert_dialog.trigger(
                                        rx.icon_button(
                                            rx.icon("trash", size=14),
                                            size="1", variant="ghost", color_scheme="red",
                                        ),
                                    ),
                                    rx.alert_dialog.content(
                                        rx.alert_dialog.title("Delete Solution"),
                                        rx.alert_dialog.description(
                                            f'Delete "{sol.name}" along with all its sub-solutions and experiments? This is irreversible.',
                                            size="2",
                                        ),
                                        rx.flex(
                                            rx.alert_dialog.cancel(
                                                rx.button("Cancel", variant="soft", color_scheme="gray"),
                                            ),
                                            rx.alert_dialog.action(
                                                rx.button(
                                                    "Delete Solution",
                                                    color_scheme="red",
                                                    on_click=lambda: State.delete_solution(sol.id),
                                                ),
                                            ),
                                            spacing="3", justify="end", margin_top="16px",
                                        ),
                                        max_width="420px",
                                    ),
                                ),
                                spacing="2", align="center",
                            ),
                        ),
                        spacing="2", align="center",
                    ),
                    justify="between", width="100%",
                ),
                # Description
                rx.cond(
                    sol.description != "",
                    rx.text(sol.description, size="2", color="var(--gray-11)", white_space="pre-wrap"),
                    rx.fragment(),
                ),
                # Inline experiments (attached to this solution)
                rx.cond(
                    sol.experiments.length() > 0,
                    rx.vstack(
                        rx.foreach(sol.experiments, render_detail_experiment),
                        spacing="2", width="100%",
                    ),
                    rx.fragment(),
                ),
                # Inline experiment form OR "Design Experiment" button — hidden for viewers
                rx.cond(
                    ~State.is_viewer,
                    rx.cond(
                        State.experiment_target_solution_id == sol.id,
                        render_inline_experiment_form(),
                        rx.button(
                            rx.icon("flask-conical", size=13),
                            "Design Experiment",
                            size="1", variant="soft", color_scheme="purple",
                            on_click=lambda: State.open_add_experiment(sol.id, sol.name),
                        ),
                    ),
                ),
                spacing="3", width="100%",
            ),
            size="2", variant="surface",
            border_left=rx.cond(
                State.target_parent_id == sol.id,
                "4px solid var(--green-9)",
                "none",
            ),
        ),
        width="100%",
        padding_left=f"calc({sol.indent_level} * 24px)",
    )


# --- SOLUTIONS PANEL ---

def render_solutions_panel() -> rx.Component:
    return rx.vstack(
        # Solution cards with inline experiments
        rx.cond(
            State.detail_solutions_with_experiments.length() > 0,
            rx.vstack(
                rx.foreach(State.detail_solutions_with_experiments, render_solution_detail_card),
                spacing="4", width="100%",
            ),
            rx.text("No solutions brainstormed yet.", color="gray", size="2"),
        ),
        # Add / Edit solution form — hidden for viewers
        rx.cond(
            ~State.is_viewer,
        rx.box(
            rx.vstack(
                rx.text(
                    rx.cond(
                        State.editing_solution_id != -1,
                        "✏️ Editing Solution",
                        rx.cond(
                            State.target_parent_id != -1,
                            f"🌿 Sub-solution under: {State.target_parent_name}",
                            "💡 Brainstorm a Solution",
                        ),
                    ),
                    size="2", weight="bold",
                    color=rx.cond(State.target_parent_id != -1, "var(--green-11)", "gray"),
                ),
                rx.input(
                    placeholder="Solution name",
                    default_value=State.new_solution_name,
                    on_blur=State.set_new_solution_name,
                    width="100%",
                ),
                rx.text_area(
                    placeholder="Description",
                    default_value=State.new_solution_desc,
                    on_blur=State.set_new_solution_desc,
                    width="100%",
                    rows="8",
                ),
                # Status selector (shown only when editing)
                rx.cond(
                    State.editing_solution_id != -1,
                    rx.select(
                        ["Ideation", "Testing", "Discarded", "Shipped"],
                        value=State.new_solution_status,
                        on_change=State.set_new_solution_status,
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                rx.flex(
                    rx.button(
                        rx.cond(
                            State.editing_solution_id != -1,
                            "Update Solution",
                            rx.cond(
                                State.target_parent_id != -1,
                                "Save Sub-Solution",
                                "Save Solution",
                            ),
                        ),
                        on_click=lambda: State.add_manual_solution(
                            State.selected_opportunity.opportunity_id
                        ),
                        color_scheme="green", variant="solid",
                    ),
                    rx.cond(
                        (State.editing_solution_id != -1) | (State.target_parent_id != -1),
                        rx.button(
                            "Cancel",
                            on_click=State.cancel_edit,
                            color_scheme="gray", variant="soft",
                        ),
                        rx.fragment(),
                    ),
                    spacing="2",
                ),
                spacing="3",
            ),
            padding="16px",
            background_color="var(--gray-3)",
            border_radius="8px",
            margin_top="2",
            width="100%",
        ),
        ),  # end rx.cond(~is_viewer)
        spacing="5",
        width="100%",
        align_items="start",
    )


# --- REASSIGN EVIDENCE DIALOG ---

def _reassign_evidence_dialog() -> rx.Component:
    """State-controlled dialog for reassigning an evidence fragment to a different opportunity."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.vstack(
                    rx.dialog.title("Reassign Evidence"),
                    rx.text(
                        "Move this evidence fragment to a different opportunity. The quote and its source interview link will be transferred.",
                        size="2",
                        color="var(--gray-11)",
                    ),
                    spacing="1",
                ),
                rx.divider(),
                rx.vstack(
                    rx.text(
                        "DESTINATION OPPORTUNITY",
                        size="1",
                        weight="bold",
                        color="var(--blue-11)",
                        letter_spacing="0.05em",
                    ),
                    rx.select(
                        State.reassign_evidence_choices,
                        placeholder="Select destination opportunity...",
                        on_change=State.set_reassign_evidence_target,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button("Cancel", variant="soft", color_scheme="gray"),
                    ),
                    rx.button(
                        rx.icon("arrow-right-left", size=14),
                        "Reassign",
                        color_scheme="blue",
                        disabled=State.reassign_evidence_target_choice == "",
                        on_click=State.confirm_reassign_evidence,
                    ),
                    spacing="3",
                    justify="end",
                    margin_top="8px",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="480px",
        ),
        open=State.is_reassign_evidence_open,
        on_open_change=State.close_reassign_evidence_dialog,
    )


# --- MAIN PAGE ---

def render_opp_view_header() -> rx.Component:
    """Read-only header section shown in normal view mode."""
    return rx.vstack(
        # Metadata badges row
        rx.flex(
            rx.badge(
                State.selected_opportunity.theme,
                color_scheme="gray", variant="solid", size="2",
            ),
            rx.badge(
                State.selected_opportunity.status,
                color_scheme=State.selected_opportunity.status_color,
                variant="soft", size="2",
            ),
            rx.text(
                f"{State.selected_opportunity.days_old} days since validated",
                size="2", color="gray",
            ),
            spacing="3", align="center",
        ),
        # Opportunity statement
        rx.text(
            State.selected_opportunity.opportunity,
            weight="bold", size="7",
            line_height="1.3",
        ),
        # Outcome + persona row
        rx.flex(
            rx.flex(
                rx.icon("target", size=14, color="var(--blue-9)"),
                rx.select.root(
                    rx.select.trigger(size="1", placeholder="Link to Outcome..."),
                    rx.select.content(
                        rx.foreach(
                            State.selectable_outcomes,
                            lambda name: rx.select.item(name, value=name),
                        ),
                    ),
                    value=State.selected_opp_outcome_name,
                    on_change=State.set_primary_outcome,
                    disabled=State.is_viewer,
                ),
                spacing="2", align="center",
            ),
            rx.flex(
                rx.foreach(
                    State.selected_opportunity.personas_affected,
                    lambda b: rx.badge(b.name, color_scheme=b.color, variant="soft", size="1"),
                ),
                spacing="2", wrap="wrap",
            ),
            spacing="4", align="center",
        ),
        # Priority scoring row
        rx.flex(
            _info_label_detail(
                "Impact",
                "How many customers are affected and how severely? Rate 1 (few/minor) to 5 (all/critical).",
            ),
            rx.flex(
                _score_dot_detail("impact", 1),
                _score_dot_detail("impact", 2),
                _score_dot_detail("impact", 3),
                _score_dot_detail("impact", 4),
                _score_dot_detail("impact", 5),
                spacing="1",
            ),
            rx.box(
                width="1px", height="16px",
                background_color="var(--gray-5)",
                margin_x="2",
            ),
            _info_label_detail(
                "Sat. Gap",
                "How dissatisfied are customers with current workarounds? Rate 1 (satisfied) to 5 (very frustrated).",
            ),
            rx.flex(
                _score_dot_detail("sat_gap", 1),
                _score_dot_detail("sat_gap", 2),
                _score_dot_detail("sat_gap", 3),
                _score_dot_detail("sat_gap", 4),
                _score_dot_detail("sat_gap", 5),
                spacing="1",
            ),
            rx.box(
                width="1px", height="16px",
                background_color="var(--gray-5)",
                margin_x="2",
            ),
            rx.text(
                f"Priority {State.selected_opportunity.priority_score}/15",
                size="2",
                color=rx.cond(
                    State.selected_opportunity.priority_score >= 11,
                    "var(--amber-11)",
                    rx.cond(
                        State.selected_opportunity.priority_score >= 6,
                        "var(--blue-11)",
                        "var(--gray-12)",
                    ),
                ),
                weight="medium",
            ),
            spacing="2", align="center", wrap="wrap",
        ),
        spacing="3",
        align_items="start",
        width="100%",
    )


def render_opp_edit_header() -> rx.Component:
    """Inline edit form shown when is_editing_opp_detail is True."""
    return rx.box(
        rx.vstack(
            rx.text(
                "EDITING OPPORTUNITY",
                text_transform="uppercase", letter_spacing="0.08em",
                size="1", weight="bold", color="var(--orange-11)",
            ),
            # Theme
            rx.vstack(
                rx.text("Theme / Category", size="2", weight="bold", color="var(--gray-12)"),
                combo_box(
                    "e.g., Usability, Pricing...",
                    State.manual_opp_theme,
                    State.set_manual_opp_theme,
                    "opp_theme",
                    State.filtered_opp_themes,
                ),
                spacing="1", width="100%", align_items="start",
            ),
            # Opportunity statement
            rx.vstack(
                rx.text("Opportunity Statement", size="2", weight="bold", color="var(--gray-12)"),
                rx.text_area(
                    default_value=State.manual_opp_statement,
                    on_blur=State.set_manual_opp_statement,
                    placeholder="I need a way to...",
                    width="100%",
                    rows="3",
                ),
                spacing="1", width="100%", align_items="start",
            ),
            # Parent opportunity
            rx.vstack(
                rx.text("Parent Opportunity", size="2", weight="bold", color="var(--gray-12)"),
                rx.select(
                    State.parent_opp_choices,
                    value=State.manual_opp_parent_id,
                    on_change=State.set_manual_opp_parent_id,
                    placeholder="None (top-level)",
                    width="100%",
                ),
                spacing="1", width="100%", align_items="start",
            ),
            # Action buttons
            rx.flex(
                rx.button(
                    rx.icon("check", size=14),
                    "Save Changes",
                    on_click=State.save_opp_detail_edit,
                    color_scheme="blue", variant="solid",
                ),
                rx.button(
                    "Cancel",
                    on_click=State.exit_opp_detail_edit,
                    color_scheme="gray", variant="soft",
                ),
                spacing="3",
            ),
            spacing="4",
            align_items="start",
            width="100%",
        ),
        padding="20px",
        background_color="var(--orange-2)",
        border="1px solid var(--orange-5)",
        border_radius="10px",
        width="100%",
    )


def render_opportunity_detail() -> rx.Component:
    return rx.vstack(
        # Top bar: back button + edit button
        rx.flex(
            rx.button(
                rx.icon("arrow-left", size=16),
                "Back to Ledger",
                variant="ghost",
                color_scheme="gray",
                on_click=State.handle_navigation("ledger"),
            ),
            rx.cond(
                State.is_editing_opp_detail | State.is_viewer,
                rx.fragment(),
                rx.flex(
                    rx.button(
                        rx.icon("pencil", size=14),
                        "Edit",
                        variant="soft",
                        color_scheme="gray",
                        on_click=State.enter_opp_detail_edit,
                    ),
                    rx.button(
                        rx.icon("git-merge", size=14),
                        "Merge",
                        variant="soft",
                        color_scheme="gray",
                        on_click=State.open_merge_dialog(State.selected_opportunity_id),
                    ),
                    rx.alert_dialog.root(
                        rx.alert_dialog.trigger(
                            rx.button(
                                rx.icon("trash", size=14),
                                "Delete",
                                variant="soft",
                                color_scheme="red",
                            ),
                        ),
                        rx.alert_dialog.content(
                            rx.alert_dialog.title("Delete Opportunity"),
                            rx.alert_dialog.description(
                                f'Delete "{State.selected_opportunity.opportunity}"? This will permanently remove all its solutions, experiments, and evidence links. This cannot be undone.',
                                size="2",
                            ),
                            rx.flex(
                                rx.alert_dialog.cancel(
                                    rx.button("Cancel", variant="soft", color_scheme="gray"),
                                ),
                                rx.alert_dialog.action(
                                    rx.button(
                                        "Delete Opportunity",
                                        color_scheme="red",
                                        on_click=State.delete_current_opportunity,
                                    ),
                                ),
                                spacing="3", justify="end", margin_top="16px",
                            ),
                            max_width="480px",
                        ),
                    ),
                    spacing="2",
                    align="center",
                ),
            ),
            justify="between",
            width="100%",
            align="center",
        ),
        # Header: view mode or edit mode
        rx.cond(
            State.is_editing_opp_detail,
            render_opp_edit_header(),
            render_opp_view_header(),
        ),
        rx.divider(),
        # 2-column body — shared header row keeps labels/divider perfectly aligned
        rx.vstack(
            # Shared column header row
            rx.flex(
                rx.box(
                    rx.text(
                        "EVIDENCE",
                        text_transform="uppercase", letter_spacing="0.08em",
                        size="1", weight="bold", color="var(--gray-12)",
                    ),
                    width="360px",
                    flex_shrink="0",
                    padding_right="32px",
                ),
                rx.box(
                    rx.text(
                        "SOLUTIONS & EXPERIMENTS",
                        text_transform="uppercase", letter_spacing="0.08em",
                        size="1", weight="bold", color="var(--gray-12)",
                    ),
                    flex="1",
                    padding_left="32px",
                ),
                width="100%",
            ),
            rx.divider(),
            # Content columns
            rx.flex(
                rx.box(
                    render_evidence_panel(),
                    width="360px",
                    flex_shrink="0",
                    border_right="1px solid var(--gray-5)",
                    padding_right="32px",
                ),
                rx.box(
                    render_solutions_panel(),
                    flex="1",
                    padding_left="32px",
                    min_width="0",
                ),
                width="100%",
                align_items="start",
            ),
            spacing="3",
            width="100%",
        ),
        transcript_drawer_panel(),
        _merge_dialog(),
        _reassign_evidence_dialog(),
        width="100%",
        max_width="1400px",
        spacing="5",
        padding_top="20px",
        align_items="start",
    )


def transcript_drawer_panel() -> rx.Component:
    """Right-side drawer showing a full interview transcript with the evidence quote highlighted."""
    return rx.drawer.root(
        rx.drawer.overlay(),
        rx.drawer.content(
            rx.cond(
                State.transcript_drawer_open,
                rx.box(
                    rx.vstack(
                        # Header: persona badge + date + close button
                        rx.flex(
                            rx.badge(
                                State.transcript_drawer_persona,
                                color_scheme=State.transcript_drawer_persona_color,
                                variant="soft",
                                size="2",
                            ),
                            rx.text(
                                State.transcript_drawer_date,
                                size="2",
                                color="var(--gray-12)",
                            ),
                            rx.spacer(),
                            rx.icon_button(
                                rx.icon("x", size=16),
                                variant="ghost",
                                color_scheme="gray",
                                on_click=State.close_transcript_drawer,
                            ),
                            align="center",
                            spacing="3",
                            width="100%",
                        ),
                        rx.divider(),
                        # Instruction banner — select mode only, hidden for viewers
                        rx.cond(
                            (~State.is_viewer) & (State.transcript_drawer_mode == "select"),
                            rx.callout.root(
                                rx.callout.icon(rx.icon("mouse-pointer-2", size=16)),
                                rx.callout.text(
                                    "Drag to select the exact quote you want to map as evidence"
                                ),
                                color_scheme="blue",
                                variant="soft",
                                size="1",
                            ),
                        ),
                        # Confirmation bar — shown when text is captured in select mode, hidden for viewers
                        rx.cond(
                            (~State.is_viewer)
                            & (State.transcript_drawer_mode == "select")
                            & (State.transcript_drawer_selection != ""),
                            rx.box(
                                rx.vstack(
                                    rx.text(
                                        State.transcript_drawer_selection,
                                        size="2",
                                        font_style="italic",
                                        color="var(--gray-12)",
                                    ),
                                    rx.hstack(
                                        rx.button(
                                            rx.icon("check", size=14),
                                            "Map as Evidence",
                                            color_scheme="blue",
                                            size="2",
                                            flex="1",
                                            on_click=State.confirm_drawer_evidence,
                                            disabled=State.is_viewer,
                                        ),
                                        rx.button(
                                            "Clear",
                                            variant="outline",
                                            color_scheme="gray",
                                            size="2",
                                            flex="1",
                                            on_click=State.clear_drawer_selection,
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),
                                    spacing="2",
                                ),
                                padding="12px 16px",
                                background_color="var(--blue-2)",
                                border="1px solid var(--blue-6)",
                                border_radius="8px",
                                width="100%",
                            ),
                        ),
                        # Transcript box — id="drawer-transcript" targets _SCROLL_TO_MARK
                        rx.box(
                            rx.html(State.transcript_drawer_html),
                            id="drawer-transcript",
                            width="100%",
                            height="calc(100vh - 100px)",
                            overflow_y="auto",
                            padding="16px",
                            background_color="var(--gray-2)",
                            border_radius="8px",
                            border="1px solid var(--gray-5)",
                            on_mouse_up=State.capture_drawer_selection,
                            user_select="text",
                            cursor="text",
                        ),
                        spacing="4",
                        padding="24px",
                        width="100%",
                    ),
                    height="100vh",
                    width="780px",
                    max_width="90vw",
                    bg="var(--gray-1)",
                    position="fixed",
                    top="0",
                    right="0",
                    overflow_y="auto",
                    box_shadow="-10px 0 30px rgba(0,0,0,0.1)",
                ),
                rx.fragment(),
            ),
        ),
        direction="right",
        open=State.transcript_drawer_open,
        on_open_change=State.close_transcript_drawer,
        dismissible=False,
    )
