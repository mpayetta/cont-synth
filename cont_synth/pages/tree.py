import reflex as rx
from cont_synth.state import State, LedgerItem, SolutionItem

def render_tree_solution(sol: SolutionItem):
    """Renders a 'Leaf' (Solution) attached to an Opportunity node."""
    return rx.box(
        rx.flex(
            # Swap icon based on if it's a root solution or a sub-branch
            rx.cond(sol.indent_level > 0, rx.icon("corner-down-right", size=14, color="var(--gray-8)"), rx.icon("git-branch", size=14, color="var(--gray-8)")),
            rx.text(sol.name, weight="medium", size="2"),
            spacing="2", align="center"
        ),
        rx.badge(sol.status, color_scheme="blue", variant="soft", size="1", margin_left="22px"),
        border_left="2px solid var(--blue-5)",
        padding_left="10px",
        margin_top="8px",
        width="100%",
        # Indent nested branches visually!
        margin_left=f"calc({sol.indent_level} * 15px)" 
    )

def render_tree_opportunity(item: LedgerItem):
    """Renders a 'Node' (Opportunity) and maps its Solutions below it."""
    return rx.vstack(
        # The vertical stem dropping down to this specific card
        rx.box(width="2px", height="20px", background_color="var(--gray-6)"),
        
        # The Opportunity Card (Now uses native rx.card for perfect dark/light mode colors!)
        rx.card(
            rx.vstack(
                rx.flex(
                    rx.badge(item.theme, color_scheme="gray", variant="solid", size="1"),
                    rx.badge(item.status, color_scheme=item.status_color, variant="soft", size="1"),
                    justify="between", width="100%", margin_bottom="2"
                ),
                rx.text(item.opportunity, weight="bold", size="3"),
                
                # Nested Solutions
                rx.box(
                    rx.cond(
                        item.solutions.length() == 0,
                        rx.text("No solutions yet.", color="gray", size="1", margin_top="2", font_style="italic"),
                        rx.foreach(item.solutions, render_tree_solution)
                    ),
                    margin_top="10px",
                    padding_top="10px",
                    border_top="1px dashed var(--gray-5)",
                    width="100%"
                ),
                align_items="start", width="100%"
            ),
            width="320px", # Fixed width so they line up neatly
            cursor="pointer",
            variant="surface", 
            _hover={"borderColor": "var(--blue-8)", "transform": "translateY(-2px)", "transition": "transform 0.2s"},
            on_click=lambda: State.open_drawer(item)
        ),
        align="center",
        spacing="0"
    )

def render_tree() -> rx.Component:
    """The master canvas for the Opportunity Solution Tree."""
    return rx.vstack(
        rx.box(
            rx.text("Opportunity Solution Tree.", weight="bold", size="6"),
            rx.text("A visual map from Business Outcomes to actionable Solutions.", color="gray", size="3"),
        ),
        rx.divider(),
        
        # Global Filter Header
        rx.flex(
            rx.text("Focus Tree on Outcome:", weight="bold", color="gray"),
            rx.select(State.outcome_names, value=State.active_outcome_name, on_change=State.change_outcome_filter, size="3", width="300px"),
            align="center", spacing="3", margin_bottom="10px"
        ),
        
        # The Top-to-Bottom Tree Canvas
        rx.box(
            rx.cond(
                State.active_outcome_name == "All Outcomes",
                
                # EMPTY STATE
                rx.center(
                    rx.vstack(
                        rx.icon("network", size=40, color="var(--gray-8)"),
                        rx.text("Select a specific Business Outcome to render its tree.", color="gray", weight="medium"),
                        align="center", spacing="3"
                    ),
                    height="400px", width="100%"
                ),
                
                # RENDER STATE: Vertical Tree layout
                rx.vstack(
                    # LEVEL 1: THE ROOT (Outcome)
                    rx.card(
                        rx.text(State.active_outcome_name, weight="bold", size="5"),
                        variant="classic",
                        color_scheme="blue",
                        size="4",
                        z_index="2"
                    ),
                    
                    # LEVEL 2 & 3: THE BRANCHES (Opportunities & Solutions)
                    rx.cond(
                        State.ledger_data.length() == 0,
                        rx.vstack(
                            rx.box(width="2px", height="30px", background_color="var(--gray-6)"),
                            rx.text("No opportunities mapped to this outcome yet.", color="gray", font_style="italic"),
                            align="center", spacing="0"
                        ),
                        rx.vstack(
                            # The main central trunk dropping from the Root
                            rx.box(width="2px", height="20px", background_color="var(--gray-6)"),
                            
                            # The horizontal row of Opportunities
                            rx.hstack(
                                rx.foreach(State.ledger_data, render_tree_opportunity),
                                spacing="6",
                                align_items="start"
                            ),
                            align="center", spacing="0"
                        )
                    ),
                    align_items="center",
                    spacing="0",
                    width="100%"
                )
            ),
            padding="40px",
            background_color="var(--gray-2)",
            border_radius="12px",
            width="100%",
            min_height="600px",
            overflow_x="auto", # Critical: Allows you to scroll sideways if you have 10+ opportunities!
            border="1px solid var(--gray-4)"
        ),
        width="100%", max_width="1400px", spacing="4", padding_top="20px"
    )