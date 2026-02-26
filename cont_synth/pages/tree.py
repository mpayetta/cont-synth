import reflex as rx
from cont_synth.state import State, LedgerItem, SolutionItem


def render_tree_solution(sol: SolutionItem):
    """Renders a 'Leaf' (Solution) attached to an Opportunity node."""
    return rx.box(
        rx.flex(
            # Swap icon based on if it's a root solution or a sub-branch
            rx.cond(
                sol.indent_level > 0,
                rx.icon("corner-down-right", size=14, color="var(--gray-8)"),
                rx.icon("git-branch", size=14, color="var(--gray-8)"),
            ),
            rx.text(sol.name, weight="medium", size="2"),
            spacing="2",
            align="center",
        ),
        rx.badge(
            sol.status,
            color_scheme="blue",
            variant="soft",
            size="1",
            margin_left="22px",
        ),
        border_left="2px solid var(--blue-5)",
        padding_left="10px",
        margin_top="8px",
        width="100%",
        # Indent nested branches visually!
        margin_left=f"calc({sol.indent_level} * 15px)",
    )


def render_tree_opportunity(item: LedgerItem):
    """Renders a 'Node' (Opportunity) and maps its Solutions below it."""
    return rx.box(
        rx.flex(
            # The Branch Icon: Drops in from the left to point at nested children
            rx.cond(
                item.indent_level > 0,
                rx.icon(
                    "corner-down-right",
                    size=24,
                    color="var(--gray-8)",
                    margin_right="3",
                    margin_top="2",
                ),
                rx.fragment(),
            ),
            # The Opportunity Card (Now more compact!)
            rx.card(
                rx.vstack(
                    rx.flex(
                        rx.badge(
                            item.theme, color_scheme="gray", variant="solid", size="1"
                        ),
                        rx.badge(
                            item.status,
                            color_scheme=item.status_color,
                            variant="soft",
                            size="1",
                        ),
                        justify="between",
                        width="100%",
                        margin_bottom="2",
                    ),
                    rx.text(item.opportunity, weight="bold", size="3"),
                    # Nested Solutions
                    rx.box(
                        rx.cond(
                            item.solutions.length() == 0,
                            rx.text(
                                "No solutions yet.",
                                color="gray",
                                size="1",
                                margin_top="2",
                                font_style="italic",
                            ),
                            rx.foreach(item.solutions, render_tree_solution),
                        ),
                        margin_top="10px",
                        padding_top="10px",
                        border_top="1px dashed var(--gray-5)",
                        width="100%",
                    ),
                    align_items="start",
                    width="100%",
                ),
                width="380px",  # Tighter, more professional width
                cursor="pointer",
                variant="surface",
                _hover={
                    "borderColor": "var(--blue-8)",
                    "transform": "translateX(4px)",
                    "transition": "transform 0.2s",
                },
                on_click=lambda: State.open_drawer(item),
            ),
            align="start",
            width="100%",
        ),
        # THE MAGIC: Pushes nested sub-opportunities horizontally to the right!
        margin_left=f"calc({item.indent_level} * 40px)",
        margin_top="16px",
        width="100%",
    )


def render_tree() -> rx.Component:
    """The master canvas for the Opportunity Solution Tree."""
    return rx.vstack(
        # --- HARMONIZED OUTCOME HEADER ---
        rx.flex(
            rx.box(
                rx.text("Opportunity Solution Tree.", weight="bold", size="6"),
                rx.text("A visual map from Business Outcomes to actionable Solutions.", color="gray", size="3"),
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
        
        # The Cascading Tree Canvas
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
                
                # RENDER STATE: Vertical Cascading Tree
                rx.vstack(
                    # LEVEL 1: THE ROOT (Outcome)
                    rx.flex(
                        rx.icon("target", size=24, color="var(--blue-11)"),
                        rx.text(State.active_outcome_name, weight="bold", size="5", color="var(--blue-11)"),
                        align="center",
                        spacing="3",
                        padding="16px",
                        background_color="var(--blue-3)",
                        border="1px solid var(--blue-5)",
                        border_radius="8px",
                        width="auto",
                        min_width="350px",
                        z_index="2"
                    ),
                    
                    # LEVEL 2+: THE BRANCHES (Opportunities & Solutions)
                    rx.box(
                        rx.cond(
                            State.ledger_data.length() == 0,
                            rx.text("No opportunities mapped to this outcome yet.", color="gray", font_style="italic", margin_top="4"),
                            rx.vstack(
                                rx.foreach(State.ledger_data, render_tree_opportunity),
                                align_items="start",
                                spacing="0",
                                width="100%"
                            )
                        ),
                        # THE CONTINUOUS TRUNK LINE
                        border_left="2px solid var(--gray-6)",
                        margin_left="28px", 
                        padding_left="24px",
                        padding_top="16px",
                        padding_bottom="40px",
                        width="100%"
                    ),
                    align_items="start",
                    spacing="0",
                    width="100%"
                )
            ),
            padding="40px",
            background_color="var(--gray-2)",
            border_radius="12px",
            width="100%",
            min_height="600px",
            overflow_x="auto",
            border="1px solid var(--gray-4)"
        ),
        width="100%", max_width="1400px", spacing="4", padding_top="20px"
    )