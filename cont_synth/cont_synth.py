import reflex as rx
from .state import State

# --- PAGE IMPORTS ---
from .pages.logs import render_logs
from .pages.synthesize import render_synthesize
from .pages.prep import render_prep
from .pages.ledger import render_ledger, opportunity_drawer
from .pages.tree import render_tree


# --- SIDEBAR COMPONENT ---
def sidebar_item(text: str, icon: str, view_name: str) -> rx.Component:
    """Renders a sidebar navigation link that highlights softly when active."""
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text, size="3", weight="medium"),
            spacing="3",
            align_items="center",
            width="100%",
            justify="start",
        ),
        width="100%",
        padding_left="16px",
        variant=rx.cond(State.current_view == view_name, "soft", "ghost"),
        color_scheme=rx.cond(State.current_view == view_name, "blue", "gray"),
        on_click=State.handle_navigation(view_name),  # The safe synchronous router!
        size="3",
    )


def sidebar() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.heading("The Catalyst", size="6", weight="bold"),
            rx.text("Continuous Discovery", color="gray", size="2"),
            spacing="1",
            margin_bottom="6",
        ),
        sidebar_item("Synthesize", "sparkles", "synthesize"),
        sidebar_item("Global Ledger", "table", "ledger"),
        sidebar_item("OST", "network", "tree"),
        sidebar_item("Pre-Meeting Prep", "target", "prep"),
        sidebar_item("Interview Logs", "archive", "logs"),
        width="300px",
        height="100vh",
        padding="24px",
        background_color="var(--gray-2)",
        border_right="1px solid var(--gray-5)",
        align_items="stretch",
    )


# --- GLOBAL NAVBAR ---
def navbar() -> rx.Component:
    return rx.flex(
        rx.flex(
            rx.icon("layers", size=20, color="var(--blue-11)"),
            rx.text("Product Workspace:", weight="bold", color="gray", size="3"),
            # The Active Product Dropdown
            rx.select.root(
                rx.select.trigger(
                    placeholder="Select Product Workspace", width="220px"
                ),
                rx.select.content(
                    rx.foreach(
                        State.products,
                        lambda p: rx.select.item(p.name, value=p.id.to_string()),
                    )
                ),
                value=State.active_product_id,
                on_change=State.change_product,
            ),
            # --- NEW: Workspace Settings (Edit/Delete) ---
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.icon_button(
                        rx.icon("settings", size=16),
                        variant="ghost",
                        color_scheme="gray",
                        on_click=State.open_manage_product,
                    )
                ),
                rx.dialog.content(
                    rx.dialog.title("Manage Product Workspace"),
                    rx.text("Workspace Name", size="2", weight="bold"),
                    rx.input(
                        value=State.edit_product_name,
                        on_change=State.set_edit_product_name,
                        margin_top="8px",
                        margin_bottom="8px",
                    ),
                    rx.flex(
                        # --- NEW: Destructive Action Confirmation ---
                        rx.alert_dialog.root(
                            rx.alert_dialog.trigger(
                                rx.button(
                                    rx.icon("trash", size=14),
                                    "Delete Workspace",
                                    color_scheme="red",
                                    variant="soft",
                                )
                            ),
                            rx.alert_dialog.content(
                                rx.alert_dialog.title("Delete Workspace"),
                                rx.alert_dialog.description(
                                    "Are you absolutely sure? This will permanently wipe this workspace and ALL of its nested opportunities, outcomes, solutions, and evidence. This cannot be undone.",
                                    size="2",
                                ),
                                rx.flex(
                                    rx.alert_dialog.cancel(
                                        rx.button(
                                            "Cancel",
                                            variant="soft",
                                            color_scheme="gray",
                                        )
                                    ),
                                    rx.alert_dialog.action(
                                        # Closes both the alert AND the parent dialog, then fires the delete!
                                        rx.dialog.close(
                                            rx.button(
                                                "Yes, delete it",
                                                color_scheme="red",
                                                on_click=State.delete_current_product,
                                            )
                                        )
                                    ),
                                    spacing="3",
                                    margin_top="16px",
                                    justify="end",
                                ),
                            ),
                        ),
                        # --- END Confirmation ---
                        rx.flex(
                            rx.dialog.close(
                                rx.button("Cancel", variant="soft", color_scheme="gray")
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Name",
                                    on_click=State.update_current_product,
                                    color_scheme="blue",
                                )
                            ),
                            spacing="3",
                        ),
                        justify="between",
                        width="100%",
                    ),
                    max_width="450px",
                ),
            ),
            # The Create Product Dialog
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button(
                        "+ New Product Workspace",
                        variant="soft",
                        size="2",
                        color_scheme="blue",
                    )
                ),
                rx.dialog.content(
                    rx.dialog.title("Create New Product Workspace"),
                    rx.input(
                        placeholder="e.g., Mobile App, Admin Dashboard...",
                        value=State.new_product_name,
                        on_change=State.set_new_product_name,
                    ),
                    rx.flex(
                        rx.dialog.close(
                            rx.button("Cancel", variant="soft", color_scheme="gray")
                        ),
                        rx.dialog.close(
                            rx.button(
                                "Create Workspace",
                                on_click=State.create_product,
                                color_scheme="blue",
                            )
                        ),
                        spacing="3",
                        justify="end",
                        margin_top="16px",
                    ),
                    max_width="400px",
                ),
            ),
            align="center",
            spacing="4",
        ),
        width="100%",
        padding="16px 40px",
        background_color="var(--gray-1)",
        border_bottom="1px solid var(--gray-5)",
        align="center",
        justify="between",
    )


# --- MAIN DASHBOARD LAYOUT ---
def index() -> rx.Component:
    return rx.box(
        opportunity_drawer(),
        rx.hstack(
            sidebar(),
            rx.vstack(
                navbar(),  # <--- INJECTED HERE
                rx.box(
                    rx.match(
                        State.current_view,
                        ("synthesize", render_synthesize()),
                        ("ledger", render_ledger()),
                        ("tree", render_tree()),
                        ("prep", render_prep()),
                        ("logs", render_logs()),
                        render_synthesize(),
                    ),
                    padding="40px",
                    width="100%",
                    height="100%",
                    overflow_y="auto",
                ),
                width="100%",
                height="100vh",
                spacing="0",
            ),
            width="100%",
            height="100vh",
            spacing="0",
        ),
        # Trigger the master router when the app boots!
        on_mount=State.load_data_for_current_view,
    )


# STRICTLY ONLY ONE APP INSTANTIATION
app = rx.App()
app.add_page(index)
