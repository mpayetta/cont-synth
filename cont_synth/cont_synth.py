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
from .pages.knowledge_base import render_knowledge_base
from .pages.workspace_members import render_workspace_members


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
            color=rx.cond(is_active, "var(--blue-9)", "var(--gray-9)"),
        ),
        rx.text(
            text,
            size="3",
            weight=rx.cond(is_active, "medium", "regular"),
            color=rx.cond(is_active, "var(--blue-9)", "var(--gray-11)"),
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
                    # Create Product Dialog (app admins only)
                    rx.cond(
                        State.is_admin,
                        rx.dialog.root(
                            rx.dialog.trigger(
                                rx.button(
                                    rx.icon("plus", size=14),
                                    "New",
                                    variant="outline",
                                    size="2",
                                    color_scheme="green",
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
                    ),
                    # Manage Workspace button (workspace admins only)
                    rx.cond(
                        State.is_workspace_admin,
                        rx.button(
                            rx.icon("settings", size=14),
                            "Manage",
                            variant="outline",
                            size="2",
                            color_scheme="amber",
                            width="100%",
                            on_click=State.handle_navigation("members"),
                        ),
                    ),  # end rx.cond(is_workspace_admin)
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
                    rx.text("P", color="#E5484D", weight="bold", size="6"),
                    rx.text("R", color="#FFC53D", weight="bold", size="6"),
                    rx.text("I", color="#30A46C", weight="bold", size="6"),
                    rx.text("S", color="#0090FF", weight="bold", size="6"),
                    rx.text("M", color="#6E56CF", weight="bold", size="6"),
                    rx.text("A", color="#E93D82", weight="bold", size="6"),
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
        rx.cond(
            ~State.is_viewer,
            sidebar_item("Synthesize", "sparkles", "synthesize"),
        ),
        sidebar_item("Opportunities", "table", "ledger"),
        rx.cond(
            ~State.is_viewer,
            sidebar_item("Pre-Meeting Prep", "target", "prep"),
        ),
        sidebar_item("Interviews", "archive", "logs"),
        sidebar_item("Participants", "users", "participants"),
        sidebar_item("Product Context", "book-open", "knowledge_base"),
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


# --- SYNTHESIS TOAST ---
def _synthesis_toast() -> rx.Component:
    """Fixed bottom-right toast showing synthesis progress or ready state across all pages."""
    show_toast = State.is_processing | State.synthesis_ready
    return rx.cond(
        show_toast,
        rx.box(
            rx.cond(
                State.synthesis_ready,
                # Ready state — clickable
                rx.hstack(
                    rx.icon("circle-check", size=18, color="#4ade80"),
                    rx.vstack(
                        rx.text("Synthesis ready!", weight="bold", size="2", color="white"),
                        rx.text("Click to review results →", size="1", color="rgba(255,255,255,0.7)"),
                        spacing="0",
                    ),
                    spacing="3",
                    align="center",
                    cursor="pointer",
                    on_click=State.go_to_review,
                ),
                # Processing state
                rx.hstack(
                    rx.spinner(size="2", color="white"),
                    rx.vstack(
                        rx.text("Synthesis running", weight="bold", size="2", color="white"),
                        rx.text(State.synthesis_status, size="1", color="rgba(255,255,255,0.7)"),
                        spacing="0",
                    ),
                    spacing="3",
                    align="center",
                ),
            ),
            position="fixed",
            bottom="24px",
            right="24px",
            width="280px",
            padding="14px 18px",
            background="var(--gray-7)",
            border_radius="10px",
            box_shadow="0 4px 24px rgba(0,0,0,0.3)",
            z_index="9999",
        ),
    )


# --- SHARED PAGE LAYOUT ---
def _page_layout(content: rx.Component, on_mount) -> rx.Component:
    """Authenticated app shell: sidebar + content area, guarded by is_authenticated."""
    return rx.box(
        rx.cond(
            State.is_authenticated,
            rx.fragment(
                rx.hstack(
                    sidebar(),
                    rx.box(
                        content,
                        padding="20px 40px",
                        flex="1",
                        min_width="0",
                        height="100%",
                        overflow_y="auto",
                    ),
                    width="100%",
                    height="100vh",
                    spacing="0",
                ),
                _synthesis_toast(),
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


def knowledge_base_page() -> rx.Component:
    return _page_layout(render_knowledge_base(), State.load_knowledge_base_page)


def workspace_members_page() -> rx.Component:
    return _page_layout(render_workspace_members(), State.load_members_page)


def login_route() -> rx.Component:
    return rx.box(login_page(), on_mount=State.load_app)


# STRICTLY ONLY ONE APP INSTANTIATION
app = rx.App(theme=rx.theme(accent_color="sky"))
app.add_page(home_page, route="/", title="PRISMA - Home")
app.add_page(synthesize_page, route="/synthesize", title="PRISMA - Synthesize")
app.add_page(synthesis_review_page, route="/review", title="PRISMA - Review Synthesis")
app.add_page(ledger_page, route="/opportunities", title="PRISMA - Opportunities")
app.add_page(opportunity_page, route="/opportunities/[opportunity_id]", title="PRISMA - Opportunity Details")
app.add_page(interviews_page, route="/interviews", title="PRISMA - Interviews")
app.add_page(interview_detail_page, route="/interviews/[interview_id]", title="PRISMA - Interview Details")
app.add_page(prep_page, route="/prep", title="PRISMA - Interview Preparation")
app.add_page(participants_page, route="/participants", title="PRISMA - Participants")
app.add_page(llm_usage_page, route="/llm-usage", title="PRISMA - LLM Usage")
app.add_page(account_page, route="/account", title="PRISMA - Account Settings")
app.add_page(knowledge_base_page, route="/knowledge-base", title="PRISMA - Knowledge Base")
app.add_page(workspace_members_page, route="/workspace/members", title="PRISMA - Workspace Members")
app.add_page(login_route, route="/login", title="PRISMA")
