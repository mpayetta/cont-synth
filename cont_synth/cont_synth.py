import reflex as rx
from .state import State

# --- PAGE IMPORTS ---
from .pages.home import render_home
from .pages.logs import render_logs
from .pages.synthesize import render_synthesize
from .pages.synthesis_review import render_synthesis_review
from .pages.prep import render_prep
from .pages.ledger import render_ledger
from .pages.opportunity import render_opportunity_detail
from .pages.interview_detail import render_interview_detail
from .pages.llm_usage import render_llm_usage
from .pages.participants import render_participants
from .pages.login import login_page
from .pages.account import render_account


# --- SIDEBAR COMPONENT ---
def sidebar_item(text: str, icon: str, view_name: str) -> rx.Component:
    """Renders a sidebar navigation link that highlights softly when active."""
    # "Synthesize" stays active on the synthesis review step
    # "Interviews" stays active when viewing a specific interview detail
    if view_name == "synthesize":
        is_active = (State.current_view == "synthesize") | (State.current_view == "synthesis_review")
    elif view_name == "logs":
        is_active = (State.current_view == "logs") | (State.current_view == "interview_detail")
    else:
        is_active = State.current_view == view_name
    return rx.hstack(
        rx.icon(
            icon,
            size=17,
            color=rx.cond(is_active, "#118AB2", "var(--gray-9)"),
        ),
        rx.text(
            text,
            size="3",
            weight=rx.cond(is_active, "medium", "regular"),
            color=rx.cond(is_active, "#118AB2", "var(--gray-11)"),
        ),
        spacing="3",
        align="center",
        width="100%",
        padding="8px 12px",
        border_radius="6px",
        background_color=rx.cond(is_active, "rgba(17, 138, 178, 0.1)", "transparent"),
        cursor="pointer",
        on_click=State.handle_navigation(view_name),
        _hover={"background_color": rx.cond(is_active, "rgba(17, 138, 178, 0.1)", "var(--gray-3)")},
    )


def _workspace_section() -> rx.Component:
    """Collapsible workspace section at the bottom of the sidebar."""
    return rx.vstack(
        # Always-visible header row — click to toggle
        rx.hstack(
            rx.hstack(
                rx.icon("layers", size=14, color="var(--gray-9)"),
                rx.text(
                    "Workspace",
                    size="1",
                    weight="bold",
                    color="var(--gray-9)",
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                ),
                align="center",
                spacing="1",
            ),
            rx.spacer(),
            # Current workspace name chip
            rx.badge(
                State.active_product_name,
                color_scheme="blue",
                variant="soft",
                size="1",
                max_width="110px",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            ),
            rx.icon(
                rx.cond(State.workspace_menu_open, "chevron-down", "chevron-right"),
                size=14,
                color="var(--gray-9)",
            ),
            align="center",
            width="100%",
            cursor="pointer",
            on_click=State.toggle_workspace_menu,
            padding="6px 2px",
            border_radius="6px",
            _hover={"background_color": "var(--gray-3)"},
        ),

        # Collapsible content
        rx.cond(
            State.workspace_menu_open,
            rx.vstack(
                # Workspace selector
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Select workspace",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            State.products,
                            lambda p: rx.select.item(p.name, value=p.id.to_string()),
                        )
                    ),
                    value=State.active_product_id,
                    on_change=State.change_product,
                    width="100%",
                ),
                # New Workspace + Manage row
                rx.grid(
                    # Create Product Dialog
                    rx.dialog.root(
                        rx.dialog.trigger(
                            rx.button(
                                rx.icon("plus", size=14),
                                "New",
                                variant="ghost",
                                size="2",
                                color_scheme="gray",
                                width="100%",
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
                    # Manage / Edit / Delete Dialog
                    rx.dialog.root(
                        rx.dialog.trigger(
                            rx.button(
                                rx.icon("settings", size=14),
                                "Manage",
                                variant="ghost",
                                size="2",
                                color_scheme="gray",
                                width="100%",
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
                    columns="2",
                    spacing="2",
                    width="100%",
                ),
                spacing="2",
                width="100%",
                padding_top="8px",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="1",
        padding_top="16px",
        border_top="1px solid var(--gray-5)",
    )


def _user_section() -> rx.Component:
    """Logged-in user row at the bottom of the sidebar with settings and logout."""
    return rx.hstack(
        rx.icon("circle-user", size=16, color="var(--gray-9)"),
        rx.text(
            State.auth_fullname,
            size="2",
            color="var(--gray-11)",
            flex="1",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        ),
        rx.icon_button(
            rx.icon("settings", size=14),
            variant="ghost",
            color_scheme="gray",
            size="1",
            on_click=State.handle_navigation("account"),
            title="Account Settings",
        ),
        rx.icon_button(
            rx.icon("log-out", size=14),
            variant="ghost",
            color_scheme="gray",
            size="1",
            on_click=State.logout,
            title="Sign Out",
        ),
        align="center",
        width="100%",
        padding_top="12px",
        border_top="1px solid var(--gray-5)",
        spacing="2",
    )


def sidebar() -> rx.Component:
    return rx.vstack(
        # App title
        rx.vstack(
            rx.hstack(
                rx.icon("triangle", size=28, color="#ffffff"),
                rx.hstack(
                    rx.text("P", color="#EF476F", weight="bold", size="6"),
                    rx.text("R", color="#F78C6B", weight="bold", size="6"),
                    rx.text("I", color="#06D6A0", weight="bold", size="6"),
                    rx.text("S", color="#118AB2", weight="bold", size="6"),
                    rx.text("M", color="#8338EC", weight="bold", size="6"),
                    spacing="1",
                ),
                spacing="2",
                align="center",
            ),
            rx.text("Refract insights into action", color="gray", size="2"),
            spacing="1",
            margin_bottom="6",
        ),
        # Navigation items
        sidebar_item("Home", "house", "home"),
        sidebar_item("Synthesize", "sparkles", "synthesize"),
        sidebar_item("Opportunities", "table", "ledger"),
        sidebar_item("Pre-Meeting Prep", "target", "prep"),
        sidebar_item("Interviews", "archive", "logs"),
        sidebar_item("Participants", "users", "participants"),
        # Push workspace section to the bottom
        rx.spacer(),
        _workspace_section(),
        _user_section(),
        width="300px",
        min_width="300px",
        max_width="300px",
        flex_shrink="0",
        overflow="hidden",
        height="100vh",
        padding="24px",
        background_color="var(--gray-2)",
        border_right="1px solid var(--gray-5)",
        align_items="stretch",
    )


# --- SHARED PAGE LAYOUT ---
def _page_layout(content: rx.Component, on_mount) -> rx.Component:
    """Authenticated app shell: sidebar + content area, guarded by is_authenticated."""
    return rx.box(
        rx.cond(
            State.is_authenticated,
            rx.hstack(
                sidebar(),
                rx.box(
                    content,
                    padding="40px",
                    flex="1",
                    min_width="0",
                    height="100%",
                    overflow_y="auto",
                ),
                width="100%",
                height="100vh",
                spacing="0",
            ),
            rx.fragment(),  # blank while auth check redirects to /login
        ),
        on_mount=on_mount,
    )


# --- PAGE FUNCTIONS ---
def home_page() -> rx.Component:
    return _page_layout(render_home(), State.load_home_page)


def synthesize_page() -> rx.Component:
    return _page_layout(render_synthesize(), State.load_synthesize_page)


def synthesis_review_page() -> rx.Component:
    return _page_layout(render_synthesis_review(), State.load_review_page)


def ledger_page() -> rx.Component:
    return _page_layout(render_ledger(), State.load_ledger_page)


def opportunity_page() -> rx.Component:
    return _page_layout(render_opportunity_detail(), State.load_opportunity_page)


def interviews_page() -> rx.Component:
    return _page_layout(render_logs(), State.load_interviews_page)


def interview_detail_page() -> rx.Component:
    return _page_layout(render_interview_detail(), State.load_interview_detail_page)


def prep_page() -> rx.Component:
    return _page_layout(render_prep(), State.load_prep_page)


def participants_page() -> rx.Component:
    return _page_layout(render_participants(), State.load_participants_page)


def llm_usage_page() -> rx.Component:
    return _page_layout(render_llm_usage(), State.load_llm_usage_page)


def account_page() -> rx.Component:
    return _page_layout(render_account(), State.load_account_page)


def login_route() -> rx.Component:
    return rx.box(login_page(), on_mount=State.load_app)


# STRICTLY ONLY ONE APP INSTANTIATION
app = rx.App(theme=rx.theme(accent_color="sky"))
app.add_page(home_page, route="/")
app.add_page(synthesize_page, route="/synthesize")
app.add_page(synthesis_review_page, route="/review")
app.add_page(ledger_page, route="/opportunities")
app.add_page(opportunity_page, route="/opportunities/[opportunity_id]")
app.add_page(interviews_page, route="/interviews")
app.add_page(interview_detail_page, route="/interviews/[interview_id]")
app.add_page(prep_page, route="/prep")
app.add_page(participants_page, route="/participants")
app.add_page(llm_usage_page, route="/llm-usage")
app.add_page(account_page, route="/account")
app.add_page(login_route, route="/login")
