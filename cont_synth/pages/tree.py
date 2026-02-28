import reflex as rx
from cont_synth.state import State, LedgerItem, SolutionItem


# --- SOLUTION CHIP ---

def render_ost_solution_chip(sol: SolutionItem) -> rx.Component:
    """Compact pill representing one solution in the OST view."""
    status_color = rx.cond(
        sol.status == "Shipped", "green",
        rx.cond(
            sol.status == "Testing", "orange",
            rx.cond(sol.status == "Discarded", "red", "blue"),
        ),
    )
    return rx.box(
        rx.vstack(
            rx.text(sol.name, size="1", weight="medium", truncate=True),
            rx.badge(sol.status, color_scheme=status_color, variant="soft", size="1"),
            spacing="1",
            align_items="start",
        ),
        padding="8px 10px",
        background_color="var(--gray-1)",
        border="1px solid var(--gray-5)",
        border_radius="6px",
        border_left=rx.cond(
            sol.indent_level > 0,
            "3px solid var(--gray-6)",
            rx.cond(
                sol.status == "Shipped", "3px solid var(--green-8)",
                rx.cond(
                    sol.status == "Testing", "3px solid var(--orange-8)",
                    rx.cond(
                        sol.status == "Discarded",
                        "3px solid var(--red-8)",
                        "3px solid var(--blue-8)",
                    ),
                ),
            ),
        ),
        min_width="140px",
        max_width="210px",
    )


# --- OPPORTUNITY ROW ---

def render_ost_opportunity(item: LedgerItem) -> rx.Component:
    """One horizontal row: opportunity card on the left, solution chips on the right."""
    return rx.flex(
        # Opportunity card
        rx.card(
            rx.vstack(
                rx.flex(
                    rx.badge(item.theme, color_scheme="gray", variant="solid", size="1"),
                    rx.badge(
                        item.status,
                        color_scheme=item.status_color,
                        variant="soft",
                        size="1",
                    ),
                    justify="between",
                    width="100%",
                ),
                rx.text(item.opportunity, weight="medium", size="2", line_height="1.4"),
                rx.flex(
                    rx.foreach(
                        item.personas_affected,
                        lambda b: rx.badge(b.name, color_scheme=b.color, variant="soft", size="1"),
                    ),
                    spacing="1",
                    wrap="wrap",
                ),
                spacing="2",
                width="100%",
                align_items="start",
            ),
            width="270px",
            flex_shrink="0",
            cursor="pointer",
            variant="surface",
            _hover={
                "border_color": "var(--blue-8)",
                "box_shadow": "0 2px 10px var(--blue-4)",
                "transition": "all 0.15s ease",
            },
            on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
        ),
        # Horizontal connector line
        rx.box(
            rx.box(
                height="2px",
                width="24px",
                background_color="var(--gray-5)",
            ),
            display="flex",
            align_items="center",
            height="100%",
            flex_shrink="0",
        ),
        # Solution chips (or empty state)
        rx.cond(
            item.solutions.length() == 0,
            rx.text(
                "No solutions yet",
                size="1",
                color="var(--gray-8)",
                font_style="italic",
            ),
            rx.flex(
                rx.foreach(item.solutions, render_ost_solution_chip),
                wrap="wrap",
                gap="2",
                align_items="center",
            ),
        ),
        align="center",
        gap="0",
        width="100%",
        padding_left=f"calc({item.indent_level} * 32px)",
    )


# --- MAIN TREE PAGE ---

def render_tree() -> rx.Component:
    """The master canvas for the Opportunity Solution Tree."""
    return rx.vstack(
        # Header
        rx.flex(
            rx.box(
                rx.text("Opportunity Solution Tree", weight="bold", size="6"),
                rx.text(
                    "A visual map from Business Outcomes to actionable Solutions.",
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
                    rx.dialog.trigger(rx.button("+ New Outcome", variant="soft", size="3")),
                    rx.dialog.content(
                        rx.dialog.title("Define Business Outcome"),
                        rx.dialog.description(
                            "What metric are we trying to move?",
                            margin_bottom="8px",
                        ),
                        rx.input(
                            placeholder="e.g., Increase Q3 Retention",
                            value=State.new_outcome_name,
                            on_change=State.set_new_outcome_name,
                            margin_bottom="12px",
                        ),
                        rx.flex(
                            rx.dialog.close(rx.button("Cancel", variant="soft", color_scheme="gray")),
                            rx.dialog.close(
                                rx.button("Save Outcome", on_click=State.create_outcome, color_scheme="blue")
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

        # OST Canvas
        rx.box(
            rx.cond(
                State.active_outcome_name == "All Outcomes",

                # Empty state
                rx.center(
                    rx.vstack(
                        rx.icon("network", size=40, color="var(--gray-8)"),
                        rx.text(
                            "Select a specific Business Outcome to render its tree.",
                            color="gray",
                            weight="medium",
                        ),
                        align="center",
                        spacing="3",
                    ),
                    height="400px",
                    width="100%",
                ),

                # Tree: Outcome node (left) + opportunities+solutions (right)
                rx.flex(
                    # Outcome node
                    rx.box(
                        rx.vstack(
                            rx.icon("target", size=22, color="var(--blue-11)"),
                            rx.text(
                                State.active_outcome_name,
                                weight="bold",
                                size="3",
                                color="var(--blue-11)",
                                text_align="center",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        padding="20px 16px",
                        background_color="var(--blue-3)",
                        border="1px solid var(--blue-6)",
                        border_radius="12px",
                        width="180px",
                        flex_shrink="0",
                        align_self="flex-start",
                    ),
                    # Short horizontal connector from outcome to trunk
                    rx.box(
                        height="2px",
                        width="28px",
                        background_color="var(--blue-5)",
                        flex_shrink="0",
                        margin_top="47px",
                    ),
                    # Opportunities + solutions, hanging from a vertical trunk
                    rx.box(
                        rx.cond(
                            State.ledger_data.length() == 0,
                            rx.text(
                                "No opportunities mapped to this outcome yet.",
                                color="gray",
                                font_style="italic",
                                padding_top="8px",
                            ),
                            rx.vstack(
                                rx.foreach(State.ledger_data, render_ost_opportunity),
                                spacing="4",
                                align_items="start",
                                width="100%",
                            ),
                        ),
                        border_left="2px solid var(--blue-4)",
                        padding_left="24px",
                        padding_top="16px",
                        padding_bottom="16px",
                        flex="1",
                        min_width="0",
                    ),
                    align_items="start",
                    gap="0",
                    width="100%",
                ),
            ),
            padding="40px",
            background_color="var(--gray-2)",
            border_radius="12px",
            border="1px solid var(--gray-4)",
            width="100%",
            min_height="600px",
            overflow_x="auto",
        ),
        width="100%",
        max_width="1400px",
        spacing="4",
        padding_top="20px",
    )
