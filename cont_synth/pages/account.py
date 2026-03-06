import reflex as rx
from cont_synth.state import State, LlmUsageItem


# ---------------------------------------------------------------------------
# Secondary left nav
# ---------------------------------------------------------------------------

def _nav_item(label: str, icon: str, section: str) -> rx.Component:
    is_active = State.account_section == section
    return rx.hstack(
        rx.icon(
            icon,
            size=15,
            color=rx.cond(is_active, "var(--blue-9)", "var(--gray-12)"),
        ),
        rx.text(
            label,
            size="2",
            weight=rx.cond(is_active, "medium", "regular"),
            color=rx.cond(is_active, "var(--blue-9)", "var(--gray-12)"),
        ),
        spacing="3",
        align="center",
        width="100%",
        padding="8px 12px",
        border_radius="6px",
        background_color=rx.cond(is_active, "rgba(17, 138, 178, 0.1)", "transparent"),
        cursor="pointer",
        on_click=State.set_account_section(section),
        _hover={"background_color": rx.cond(is_active, "rgba(17, 138, 178, 0.1)", "var(--gray-3)")},
    )


def _secondary_nav() -> rx.Component:
    return rx.vstack(
        _nav_item("Settings", "settings", "settings"),
        rx.cond(
            State.is_admin,
            _nav_item("LLM Usage", "bar-chart-2", "llm_usage"),
        ),
        _nav_item("Danger Zone", "shield-alert", "danger_zone"),
        spacing="1",
        width="180px",
        flex_shrink="0",
        padding_top="4px",
    )


# ---------------------------------------------------------------------------
# Shared card / header helpers
# ---------------------------------------------------------------------------

def _section_card(*children, **kwargs) -> rx.Component:
    return rx.box(
        *children,
        padding="24px",
        border_radius="8px",
        border="1px solid var(--gray-5)",
        background_color="var(--gray-1)",
        width="100%",
        **kwargs,
    )


def _section_header(title: str, description: str = "") -> rx.Component:
    return rx.vstack(
        rx.text(title, size="3", weight="bold", color="var(--gray-12)"),
        rx.cond(
            description != "",
            rx.text(description, size="2", color="var(--gray-12)"),
            rx.fragment(),
        ),
        spacing="1",
        margin_bottom="16px",
    )


# ---------------------------------------------------------------------------
# Settings view (Profile + API Keys + Security)
# ---------------------------------------------------------------------------

def _profile_section() -> rx.Component:
    return _section_card(
        _section_header("Profile", "Update your display name and username."),
        rx.hstack(
            rx.vstack(
                rx.text("Username", size="2", weight="medium"),
                rx.input(
                    value=State.settings_username,
                    on_change=State.set_settings_username,
                    width="100%",
                ),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("Full Name", size="2", weight="medium"),
                rx.input(
                    value=State.settings_fullname,
                    on_change=State.set_settings_fullname,
                    width="100%",
                ),
                spacing="1",
                flex="1",
            ),
            spacing="4",
            width="100%",
        ),
    )


def _api_keys_section() -> rx.Component:
    return _section_card(
        _section_header(
            "API Keys",
            "Keys saved here are stored in the database and override the GEMINI_API_KEY environment variable.",
        ),
        rx.vstack(
            rx.hstack(
                rx.icon("bot", size=14, color="var(--gray-12)"),
                rx.text("Gemini API Key", size="2", weight="medium"),
                spacing="2",
                align="center",
            ),
            rx.text(
                "Used for synthesis, deduplication, and pre-meeting prep generation.",
                size="1",
                color="var(--gray-12)",
            ),
            rx.hstack(
                rx.input(
                    type=rx.cond(State.show_api_key, "text", "password"),
                    placeholder="AIza...",
                    value=State.settings_gemini_api_key,
                    on_change=State.set_settings_gemini_api_key,
                    flex="1",
                    font_family="monospace",
                    font_size="13px",
                ),
                rx.icon_button(
                    rx.cond(
                        State.show_api_key,
                        rx.icon("eye-off", size=14),
                        rx.icon("eye", size=14),
                    ),
                    variant="ghost",
                    color_scheme="gray",
                    size="2",
                    on_click=State.toggle_show_api_key,
                    title=rx.cond(State.show_api_key, "Hide key", "Show key"),
                ),
                spacing="2",
                width="100%",
                align="center",
            ),
            spacing="2",
            width="100%",
        ),
    )


def _security_section() -> rx.Component:
    return _section_card(
        _section_header("Security", "Change your login password. Leave blank to keep the current one."),
        rx.hstack(
            rx.vstack(
                rx.text("New Password", size="2", weight="medium"),
                rx.input(
                    type="password",
                    placeholder="Min. 6 characters",
                    value=State.settings_new_password,
                    on_change=State.set_settings_new_password,
                    width="100%",
                ),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("Confirm Password", size="2", weight="medium"),
                rx.input(
                    type="password",
                    placeholder="Re-enter new password",
                    value=State.settings_confirm_password,
                    on_change=State.set_settings_confirm_password,
                    width="100%",
                ),
                spacing="1",
                flex="1",
            ),
            spacing="4",
            width="100%",
        ),
    )


def _settings_feedback() -> rx.Component:
    return rx.vstack(
        rx.cond(
            State.settings_error != "",
            rx.callout.root(
                rx.callout.icon(rx.icon("triangle-alert", size=16)),
                rx.callout.text(State.settings_error, size="2"),
                color_scheme="red",
                variant="soft",
                width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            State.settings_success != "",
            rx.callout.root(
                rx.callout.icon(rx.icon("circle-check", size=16)),
                rx.callout.text(State.settings_success, size="2"),
                color_scheme="green",
                variant="soft",
                width="100%",
            ),
            rx.fragment(),
        ),
        spacing="2",
        width="100%",
    )


def _settings_view() -> rx.Component:
    return rx.vstack(
        rx.text("Settings", size="5", weight="bold", color="var(--gray-12)"),
        _profile_section(),
        _api_keys_section(),
        _security_section(),
        _settings_feedback(),
        rx.flex(
            rx.button(
                rx.icon("save", size=14),
                "Save Changes",
                on_click=State.save_account_settings,
                color_scheme="blue",
                size="3",
            ),
            justify="end",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ---------------------------------------------------------------------------
# LLM Usage view
# ---------------------------------------------------------------------------

def _stat_card(label: str, value: rx.Var) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                label,
                size="1",
                color="var(--gray-12)",
                weight="medium",
                text_transform="uppercase",
                letter_spacing="0.05em",
            ),
            rx.text(value, size="7", weight="bold", color="var(--gray-12)"),
            spacing="1",
            align="start",
        ),
        padding="20px 24px",
        border_radius="8px",
        border="1px solid var(--gray-5)",
        background_color="var(--gray-1)",
        flex="1",
    )


def _operation_badge(operation: str) -> rx.Component:
    color = rx.match(
        operation,
        ("synthesis", "blue"),
        ("dedupe", "violet"),
        ("prep", "green"),
        "gray",
    )
    return rx.badge(operation, color_scheme=color, variant="soft")


def _show_usage_row(item: LlmUsageItem) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.created_at, size="2", color="var(--gray-12)")),
        rx.table.cell(
            rx.badge(item.model_name, color_scheme="gray", variant="outline", size="1")
        ),
        rx.table.cell(_operation_badge(item.operation)),
        rx.table.cell(
            rx.cond(
                item.interview_id > 0,
                rx.link(
                    rx.hstack(
                        rx.icon("external-link", size=11, color="var(--blue-9)"),
                        rx.text(f"#{item.interview_id}", size="2", color="var(--blue-11)"),
                        spacing="1",
                        align="center",
                    ),
                    on_click=State.open_interview_detail(item.interview_id),
                    cursor="pointer",
                    _hover={"opacity": "0.75"},
                ),
                rx.text("—", size="2", color="var(--gray-12)"),
            )
        ),
        rx.table.cell(rx.text(item.prompt_tokens, size="2")),
        rx.table.cell(rx.text(item.output_tokens, size="2")),
        rx.table.cell(rx.text(item.total_tokens, size="2", weight="medium")),
    )


def _llm_usage_view() -> rx.Component:
    return rx.vstack(
        rx.text("LLM Usage", size="5", weight="bold", color="var(--gray-12)"),
        rx.text(
            "Track token consumption and cost drivers across all AI operations.",
            size="2",
            color="var(--gray-12)",
        ),
        rx.hstack(
            _stat_card("Total Tokens Used", State.llm_total_tokens),
            _stat_card("Synthesis Calls", State.llm_synthesis_count),
            _stat_card("Deduplication Calls", State.llm_dedupe_count),
            spacing="4",
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Date"),
                    rx.table.column_header_cell("Model"),
                    rx.table.column_header_cell("Operation"),
                    rx.table.column_header_cell("Interview"),
                    rx.table.column_header_cell("Prompt Tokens"),
                    rx.table.column_header_cell("Output Tokens"),
                    rx.table.column_header_cell("Total Tokens"),
                )
            ),
            rx.table.body(rx.foreach(State.llm_usage_logs, _show_usage_row)),
            width="100%",
            variant="surface",
        ),
        rx.cond(
            State.llm_usage_logs.length() == 0,
            rx.vstack(
                rx.icon("bar-chart-2", size=32, color="var(--gray-6)"),
                rx.text("No LLM calls recorded yet.", color="var(--gray-12)", size="3"),
                align="center",
                padding_y="40px",
                width="100%",
            ),
            rx.fragment(),
        ),
        spacing="4",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Danger Zone view
# ---------------------------------------------------------------------------

def _danger_zone_view() -> rx.Component:
    return rx.vstack(
        rx.text("Danger Zone", size="5", weight="bold", color="#E5484D"),
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Wipe All Data", size="3", weight="medium", color="var(--gray-12)"),
                        rx.text(
                            "Permanently delete all interviews, opportunities, solutions, outcomes, participants, and personas. Your user account is preserved.",
                            size="2",
                            color="var(--gray-12)",
                        ),
                        spacing="1",
                        flex="1",
                    ),
                    rx.alert_dialog.root(
                        rx.alert_dialog.trigger(
                            rx.button(
                                rx.icon("trash-2", size=14),
                                "Wipe All Data",
                                color_scheme="red",
                                variant="soft",
                                size="2",
                            ),
                        ),
                        rx.alert_dialog.content(
                            rx.alert_dialog.title("Wipe all data?"),
                            rx.alert_dialog.description(
                                "This permanently deletes every interview, opportunity, solution, outcome, participant, persona, and workspace. Your login is preserved. This cannot be undone.",
                                size="2",
                            ),
                            rx.flex(
                                rx.alert_dialog.cancel(
                                    rx.button("Cancel", variant="soft", color_scheme="gray"),
                                ),
                                rx.alert_dialog.action(
                                    rx.button(
                                        "Yes, wipe everything",
                                        color_scheme="red",
                                        on_click=State.wipe_database,
                                    ),
                                ),
                                gap="3",
                                justify="end",
                                margin_top="16px",
                            ),
                        ),
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            padding="24px",
            border_radius="8px",
            border="1px solid var(--red-6)",
            background_color="var(--red-1)",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Full page
# ---------------------------------------------------------------------------

def render_account() -> rx.Component:
    return rx.vstack(
        # Page header
        rx.vstack(
            rx.text("Account", size="7", weight="bold"),
            rx.text(
                "Manage your profile, API keys, and application data.",
                size="3",
                color="var(--gray-12)",
            ),
            spacing="1",
            margin_bottom="8px",
        ),
        rx.divider(),
        # Two-column layout: secondary nav + content
        rx.hstack(
            _secondary_nav(),
            rx.box(
                width="1px",
                min_height="400px",
                background_color="var(--gray-5)",
                flex_shrink="0",
            ),
            rx.box(
                rx.cond(
                    State.account_section == "settings",
                    _settings_view(),
                    rx.cond(
                        (State.account_section == "llm_usage") & State.is_admin,
                        _llm_usage_view(),
                        _danger_zone_view(),
                    ),
                ),
                flex="1",
                min_width="0",
            ),
            spacing="6",
            align="start",
            width="100%",
        ),
        width="100%",
        max_width="1000px",
        spacing="5",
        padding_top="20px",
        padding_bottom="40px",
    )
