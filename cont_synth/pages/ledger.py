import reflex as rx
from cont_synth.state import State, LedgerItem, PersonaBadge, QuoteItem, SolutionItem

# --- HELPER COMPONENTS ---
def render_persona_badge(badge: PersonaBadge):
    """Helper to render individual persona pills."""
    return rx.badge(badge.name, color_scheme=badge.color, variant="soft")

def render_quote(q: QuoteItem):
    """Renders a sleek card for an individual quote inside the modal."""
    return rx.card(
        rx.vstack(
            rx.flex(
                rx.badge(q.persona_name, color_scheme=q.persona_color, variant="soft", size="2"),
                # The Trash icon dynamically passes the current opportunity and the quote's interview ID
                rx.icon_button(
                    rx.icon("trash", size=14), 
                    size="1", variant="ghost", color_scheme="red", 
                    on_click=lambda: State.delete_evidence(State.selected_opportunity.opportunity_id, q.interview_id)
                ),
                justify="between", width="100%", align="center"
            ),
            rx.text(f'"{q.text}"', size="3", font_style="italic", color="var(--slate-11)"),
            spacing="3"
        ),
        size="2", width="100%", variant="surface", flex_shrink="0"  
    )

def render_solution(sol: SolutionItem):
    """Renders a sleek card for an individual solution idea with Edit/Branch controls."""
    return rx.box(
        rx.card(
            rx.vstack(
                rx.flex(
                    rx.flex(
                        rx.cond(sol.indent_level > 0, rx.icon("corner-down-right", size=14, color="var(--gray-8)"), rx.fragment()),
                        rx.text(sol.name, weight="bold", size="3", color="var(--blue-11)"),
                        spacing="2", align="center"
                    ),
                    rx.flex(
                        rx.badge(sol.status, color_scheme="blue", variant="soft", size="1"),
                        # --- FIX: Pass both the ID and the Name to the backend ---
                        rx.icon_button(rx.icon("git-branch", size=14), size="1", variant="ghost", color_scheme="blue", on_click=lambda: State.set_target_parent(sol.id, sol.name)),
                        rx.icon_button(rx.icon("pencil", size=14), size="1", variant="ghost", color_scheme="gray", on_click=lambda: State.start_edit_solution(sol)),
                        rx.icon_button(rx.icon("trash", size=14), size="1", variant="ghost", color_scheme="red", on_click=lambda: State.delete_solution(sol.id)),
                        spacing="2", align="center"
                    ),
                    justify="between", width="100%"
                ),
                rx.text(sol.description, size="2", color="gray"),
                spacing="2"
            ),
            size="2", width="100%", variant="surface",
            
            # --- THE MAGIC: Add a green left-border highlight if this card is the active parent! ---
            border_left=rx.cond(State.target_parent_id == sol.id, "4px solid var(--green-9)", "1px solid var(--gray-4)")
        ),
        width="100%",
        padding_left=f"calc({sol.indent_level} * 30px)" 
    )

def show_ledger_row(item: LedgerItem):
    """Renders a single row in the Global Ledger table."""
    return rx.table.row(
        rx.table.cell(rx.badge(item.theme, color_scheme="gray", variant="solid")),
        rx.table.cell(rx.flex(rx.foreach(item.personas_affected, render_persona_badge), spacing="2", wrap="wrap")),
        rx.table.cell(
            rx.vstack(
                rx.text(item.opportunity),
                rx.cond(item.is_cross_functional, rx.badge("🌟 Cross-Persona Impact", color_scheme="amber", variant="soft", size="1"), rx.fragment()),
                spacing="1"
            )
        ),
        rx.table.cell(rx.badge(item.status, color_scheme=item.status_color, variant="soft", size="2")),
        rx.table.cell(item.days_old),
        # --- Action Buttons (Open Workspace + Edit + Delete) ---
        rx.table.cell(
            rx.flex(
                rx.button(
                    "Open", 
                    variant="soft", 
                    color_scheme="blue", 
                    size="2", 
                    on_click=lambda: State.open_drawer(item)
                ),
                rx.icon_button(
                    rx.icon("pencil", size=16), 
                    variant="soft", 
                    color_scheme="gray", 
                    size="2", 
                    on_click=lambda: State.start_edit_opportunity(item.opportunity_id, item.theme, item.opportunity)
                ),
                rx.icon_button(
                    rx.icon("trash", size=16), 
                    variant="soft", 
                    color_scheme="red", 
                    size="2", 
                    on_click=lambda: State.delete_opportunity(item.opportunity_id)
                ),
                spacing="2", align="center"
            )
        ),
        style=rx.cond(item.is_cross_functional, {"backgroundColor": "var(--amber-2)"}, {})
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
                    rx.text("🔗 Map Missed Evidence", size="2", weight="bold", color="gray"),
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
                        rx.cond(
                            (State.editing_solution_id == -1)
                            & (State.target_parent_id == -1),
                            rx.button(
                                rx.icon("sparkles", size=14),
                                "AI Brainstorm",
                                on_click=lambda: State.generate_competing_solutions(
                                    State.selected_opportunity.opportunity_id
                                ),
                                loading=State.is_generating_solutions,
                                color_scheme="amber",
                                variant="soft",
                            ),
                            rx.fragment(),
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
            rx.tabs.trigger(
                "Experiments (Soon)", value="experiments", disabled=True
            ),
            width="100%",
        ),
        render_evidence_tab(),
        render_solutions_tab(),
        default_value="evidence",
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
                        width="100%", padding="24px"
                    ),
                    height="100vh", width="600px", max_width="90vw", bg="var(--gray-1)", position="fixed", top="0", right="0", overflow_y="auto", box_shadow="-10px 0 30px rgba(0,0,0,0.1)"
                ),
                rx.fragment() 
            )
        ),
        direction="right",
        open=State.is_drawer_open,
        on_open_change=State.handle_drawer_change
    )

def render_ledger() -> rx.Component:
    """The main view for the Global Ledger."""
    return rx.vstack(
        # --- NEW OUTCOME HEADER ---
        rx.flex(
            rx.box(
                rx.text("The Single Source of Truth.", weight="bold", size="6"),
                rx.text("Filter by business outcome to focus your Continuous Discovery efforts.", color="gray", size="3"),
            ),
            rx.flex(
                rx.select(State.outcome_names, value=State.active_outcome_name, on_change=State.change_outcome_filter, size="3", width="250px"),
                rx.dialog.root(
                    rx.dialog.trigger(rx.button("+ New Outcome", variant="soft", size="3")),
                    rx.dialog.content(
                        rx.dialog.title("Define Business Outcome"),
                        rx.dialog.description("What metric are we trying to move?", margin_bottom="8px"),
                        rx.input(placeholder="e.g., Increase Q3 Retention", value=State.new_outcome_name, on_change=State.set_new_outcome_name, margin_bottom="12px"),
                        rx.flex(
                            rx.dialog.close(rx.button("Cancel", variant="soft", color_scheme="gray")),
                            rx.dialog.close(rx.button("Save Outcome", on_click=State.create_outcome, color_scheme="blue")),
                            spacing="3", justify="end"
                        ),
                        max_width="450px"
                    )
                ),
                spacing="3", align="center"
            ),
            justify="between", width="100%", margin_bottom="10px", align="center"
        ),
        rx.divider(),
        
        # --- Action Bar & Opportunity Form Dialog ---
        rx.flex(
            rx.button("Refresh Global Ledger", on_click=State.load_ledger, size="2", variant="outline", color_scheme="gray"),
            
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button("+ New Opportunity", size="2", color_scheme="blue", variant="soft", on_click=State.open_opp_dialog)
                ),
                rx.dialog.content(
                    rx.dialog.title(rx.cond(State.editing_opp_id != -1, "Edit Opportunity", "Create Manual Opportunity")),
                    rx.dialog.description("Manually add or update an opportunity.", margin_bottom="8px"),
                    
                    rx.vstack(
                        rx.text("Theme / Category", size="2", weight="bold"),
                        rx.input(placeholder="e.g., Usability, Pricing...", value=State.manual_opp_theme, on_change=State.set_manual_opp_theme, width="100%"),
                        
                        rx.text("Opportunity Statement", size="2", weight="bold", margin_top="2"),
                        rx.text_area(placeholder="I need a way to...", value=State.manual_opp_statement, on_change=State.set_manual_opp_statement, width="100%"),
                        spacing="2", width="100%", margin_bottom="12px"
                    ),
                    
                    rx.flex(
                        rx.button("Cancel", variant="soft", color_scheme="gray", on_click=State.close_opp_dialog),
                        rx.button("Save Opportunity", on_click=State.save_manual_opportunity, color_scheme="blue"),
                        spacing="3", justify="end"
                    ),
                    max_width="500px"
                ),
                open=State.is_opp_dialog_open,
                on_open_change=State.handle_opp_dialog_change
            ),
            spacing="3", width="100%", justify="start", margin_bottom="4"
        ),

        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell("Theme"),
                rx.table.column_header_cell("Personas Affected"),
                rx.table.column_header_cell("Master Opportunity"),
                rx.table.column_header_cell("Status"),
                rx.table.column_header_cell("Days Since Validated"),
                rx.table.column_header_cell("Workspace"),
            )),
            rx.table.body(rx.foreach(State.ledger_data, show_ledger_row)),
            width="100%", variant="surface"
        ),
        width="100%", max_width="1400px", spacing="4", padding_top="20px"
    )