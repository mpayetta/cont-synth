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


# --- MAIN DASHBOARD LAYOUT ---
def index() -> rx.Component:
    return rx.box(
        opportunity_drawer(),
        rx.hstack(
            sidebar(),
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
                height="100vh",
                overflow_y="auto",
            ),
            width="100%",
            height="100vh",
            spacing="0",
        ),
        on_mount=State.load_ledger,
    )


# STRICTLY ONLY ONE APP INSTANTIATION
app = rx.App()
app.add_page(index)
