import reflex as rx
from cont_synth.state import State


# ── Helpers ────────────────────────────────────────────────────────────────────

def _role_badge(role: str) -> rx.Component:
    color = rx.cond(
        role == "admin",
        "sky",
        rx.cond(role == "viewer", "gray", "green"),
    )
    return rx.badge(role, color_scheme=color, variant="soft", size="1")


def _action_badge(action: str) -> rx.Component:
    color = rx.cond(
        action == "delete",
        "red",
        rx.cond(
            action == "role_change",
            "sky",
            rx.cond(action == "status_change", "amber", "gray"),
        ),
    )
    return rx.badge(action, color_scheme=color, variant="soft", size="1")


# ── Workspace Details tab ───────────────────────────────────────────────────────

def _workspace_details_tab_content() -> rx.Component:
    return rx.vstack(
        # Rename section
        rx.vstack(
            rx.text("Workspace Name", size="3", weight="bold"),
            rx.text(
                "Update the display name for this workspace.",
                size="2",
                color="var(--gray-10)",
            ),
            rx.hstack(
                rx.input(
                    value=State.edit_product_name,
                    on_change=State.set_edit_product_name,
                    flex="1",
                    size="3",
                ),
                rx.button(
                    "Save Name",
                    on_click=State.update_current_product,
                    color_scheme="blue",
                    size="3",
                ),
                spacing="3",
                width="100%",
                align="end",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),

        rx.separator(width="100%"),

        # Danger Zone
        rx.vstack(
            rx.hstack(
                rx.icon("shield-alert", size=16, color="var(--red-9)"),
                rx.text("Danger Zone", size="3", weight="bold", color="var(--red-9)"),
                spacing="2",
                align="center",
            ),
            # Wipe workspace data
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Wipe Workspace Data", size="3", weight="medium", color="var(--gray-12)"),
                        rx.text(
                            "Permanently delete all interviews, opportunities, solutions, outcomes, and participants. The workspace itself and your account are preserved.",
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
                                "Wipe Workspace Data",
                                color_scheme="red",
                                variant="soft",
                                size="2",
                            ),
                        ),
                        rx.alert_dialog.content(
                            rx.alert_dialog.title("Wipe workspace data?"),
                            rx.alert_dialog.description(
                                "This permanently deletes all interviews, opportunities, solutions, outcomes, and participants in the current workspace. The workspace itself and your login are preserved. This cannot be undone.",
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
                                gap="8px",
                                justify="end",
                                margin_top="16px",
                            ),
                        ),
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                padding="24px",
                border_radius="8px",
                border="1px solid var(--red-6)",
                background_color="var(--red-1)",
                width="100%",
            ),
            # Delete workspace entirely
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text("Delete Workspace", size="3", weight="medium", color="var(--gray-12)"),
                        rx.text(
                            "Permanently remove this workspace and all of its data. You must be the workspace owner. This cannot be undone.",
                            size="2",
                            color="var(--gray-12)",
                        ),
                        spacing="1",
                        flex="1",
                    ),
                    rx.alert_dialog.root(
                        rx.alert_dialog.trigger(
                            rx.button(
                                rx.icon("trash", size=14),
                                "Delete Workspace",
                                color_scheme="red",
                                variant="solid",
                                size="2",
                            ),
                        ),
                        rx.alert_dialog.content(
                            rx.alert_dialog.title("Delete Workspace"),
                            rx.alert_dialog.description(
                                "Are you absolutely sure? This will permanently wipe this workspace and ALL of its nested opportunities, outcomes, solutions, and evidence. This cannot be undone.",
                                size="2",
                            ),
                            rx.flex(
                                rx.alert_dialog.cancel(
                                    rx.button("Cancel", variant="soft", color_scheme="gray"),
                                ),
                                rx.alert_dialog.action(
                                    rx.button(
                                        "Yes, delete it",
                                        color_scheme="red",
                                        on_click=State.delete_current_product,
                                    ),
                                ),
                                gap="8px",
                                justify="end",
                                margin_top="16px",
                            ),
                        ),
                    ),
                    spacing="4",
                    align="center",
                    width="100%",
                ),
                padding="24px",
                border_radius="8px",
                border="1px solid var(--red-6)",
                background_color="var(--red-1)",
                width="100%",
            ),
            spacing="4",
            align="start",
            width="100%",
        ),

        spacing="6",
        align="start",
        width="100%",
    )


# ── Members tab ────────────────────────────────────────────────────────────────

def _member_row(member) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.avatar(
                    fallback=member.fullname[:1],
                    size="2",
                    color_scheme="blue",
                    variant="soft",
                ),
                rx.vstack(
                    rx.text(member.fullname, size="2", weight="medium"),
                    rx.text(member.username, size="1", color="var(--gray-10)"),
                    spacing="0",
                    align="start",
                ),
                align="center",
                spacing="2",
            )
        ),
        rx.table.cell(_role_badge(member.role)),
        rx.table.cell(
            rx.text(member.joined_at, size="1", color="var(--gray-10)")
        ),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    State.is_workspace_admin & ~member.is_owner,
                    rx.select.root(
                        rx.select.trigger(size="1", variant="ghost"),
                        rx.select.content(
                            rx.select.item("admin", value="admin"),
                            rx.select.item("member", value="member"),
                            rx.select.item("viewer", value="viewer"),
                        ),
                        value=member.role,
                        on_change=lambda new_role: State.update_member_role(member.member_id, new_role),
                        size="1",
                    ),
                ),
                rx.cond(
                    State.is_workspace_admin & ~member.is_owner,
                    rx.icon_button(
                        rx.icon("x", size=14),
                        variant="ghost",
                        color_scheme="red",
                        size="1",
                        on_click=State.remove_member(member.member_id),
                    ),
                ),
                spacing="2",
                align="center",
            )
        ),
        align="center",
    )


def _members_table() -> rx.Component:
    return rx.box(
        rx.cond(
            State.workspace_members.length() > 0,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Member"),
                        rx.table.column_header_cell("Role"),
                        rx.table.column_header_cell("Joined"),
                        rx.table.column_header_cell("Actions"),
                    )
                ),
                rx.table.body(
                    rx.foreach(State.workspace_members, _member_row)
                ),
                width="100%",
            ),
            rx.text(
                "No members yet. Invite someone below.",
                size="2",
                color="var(--gray-9)",
            ),
        ),
    )


def _invite_section() -> rx.Component:
    return rx.cond(
        State.is_workspace_admin,
        rx.vstack(
            rx.text("Invite Existing User", size="3", weight="bold"),
            rx.text(
                "Add a user who already has an account to this workspace.",
                size="2",
                color="var(--gray-10)",
            ),
            rx.hstack(
                rx.input(
                    placeholder="Username",
                    value=State.invite_username,
                    on_change=State.set_invite_username,
                    flex="1",
                ),
                rx.select.root(
                    rx.select.trigger(placeholder="Role"),
                    rx.select.content(
                        rx.select.item("admin", value="admin"),
                        rx.select.item("member", value="member"),
                        rx.select.item("viewer", value="viewer"),
                    ),
                    value=State.invite_role,
                    on_change=State.set_invite_role,
                    width="120px",
                ),
                rx.button(
                    "Invite",
                    on_click=State.invite_member_to_product,
                    color_scheme="blue",
                ),
                spacing="2",
                align="end",
                width="100%",
            ),
            rx.cond(
                State.invite_error != "",
                rx.text(State.invite_error, size="1", color="var(--red-9)"),
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
    )


def _create_user_section() -> rx.Component:
    return rx.cond(
        State.is_admin,
        rx.vstack(
            rx.separator(width="100%"),
            rx.text("Create New User", size="3", weight="bold"),
            rx.text(
                "Create a brand-new account and add them directly to this workspace.",
                size="2",
                color="var(--gray-10)",
            ),
            rx.vstack(
                rx.hstack(
                    rx.input(
                        placeholder="Username",
                        value=State.create_user_username,
                        on_change=State.set_create_user_username,
                        flex="1",
                    ),
                    rx.input(
                        placeholder="Full name",
                        value=State.create_user_fullname,
                        on_change=State.set_create_user_fullname,
                        flex="1",
                    ),
                    spacing="3",
                    width="100%",
                ),
                rx.hstack(
                    rx.input(
                        placeholder="Password",
                        type="password",
                        value=State.create_user_password,
                        on_change=State.set_create_user_password,
                        flex="1",
                    ),
                    rx.select.root(
                        rx.select.trigger(placeholder="Workspace role"),
                        rx.select.content(
                            rx.select.item("admin", value="admin"),
                            rx.select.item("member", value="member"),
                            rx.select.item("viewer", value="viewer"),
                        ),
                        value=State.create_user_workspace_role,
                        on_change=State.set_create_user_workspace_role,
                        flex="1",
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            rx.button(
                "Create & Add to Workspace",
                on_click=State.create_workspace_user,
                color_scheme="blue",
                width="fit-content",
            ),
            rx.cond(
                State.create_user_error != "",
                rx.text(State.create_user_error, size="1", color="var(--red-9)"),
            ),
            spacing="4",
            align="start",
            width="100%",
        ),
    )


def _members_tab_content() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.text("Current Members", size="3", weight="bold"),
            _members_table(),
            spacing="3",
            align="start",
            width="100%",
        ),
        _invite_section(),
        _create_user_section(),
        spacing="6",
        align="start",
        width="100%",
    )


# ── Audit Log tab ──────────────────────────────────────────────────────────────

def _audit_filter_bar() -> rx.Component:
    return rx.hstack(
        rx.select.root(
            rx.select.trigger(placeholder="All actions"),
            rx.select.content(
                rx.select.item("create", value="create"),
                rx.select.item("update", value="update"),
                rx.select.item("delete", value="delete"),
                rx.select.item("status_change", value="status_change"),
                rx.select.item("role_change", value="role_change"),
            ),
            value=State.audit_filter_action,
            on_change=State.set_audit_filter_action,
            width="160px",
        ),
        rx.select.root(
            rx.select.trigger(placeholder="All entity types"),
            rx.select.content(
                rx.select.item("interview", value="interview"),
                rx.select.item("opportunity", value="opportunity"),
                rx.select.item("solution", value="solution"),
                rx.select.item("experiment", value="experiment"),
                rx.select.item("evidence", value="evidence"),
                rx.select.item("outcome", value="outcome"),
                rx.select.item("member", value="member"),
            ),
            value=State.audit_filter_entity_type,
            on_change=State.set_audit_filter_entity_type,
            width="180px",
        ),
        rx.cond(
            (State.audit_filter_action != "") | (State.audit_filter_entity_type != ""),
            rx.button(
                "Clear",
                variant="ghost",
                color_scheme="gray",
                size="2",
                on_click=State.clear_audit_filters,
            ),
        ),
        spacing="2",
        align="center",
        wrap="wrap",
    )


def _audit_log_row(entry) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(entry.created_at, size="1", color="var(--gray-10)", white_space="nowrap")
        ),
        rx.table.cell(
            rx.text(entry.username, size="2", weight="medium")
        ),
        rx.table.cell(_action_badge(entry.action)),
        rx.table.cell(
            rx.badge(entry.entity_type, variant="outline", size="1")
        ),
        rx.table.cell(
            rx.text(entry.entity_id, size="1", color="var(--gray-10)")
        ),
        rx.table.cell(
            rx.text(entry.detail, size="1", color="var(--gray-11)")
        ),
        align="center",
    )


def _audit_pagination() -> rx.Component:
    return rx.hstack(
        rx.icon_button(
            rx.icon("chevron-left", size=14),
            variant="ghost",
            size="1",
            disabled=~State.audit_log_has_prev,
            on_click=State.audit_log_prev_page,
        ),
        rx.text(State.audit_log_page_label, size="1", color="var(--gray-10)"),
        rx.icon_button(
            rx.icon("chevron-right", size=14),
            variant="ghost",
            size="1",
            disabled=~State.audit_log_has_next,
            on_click=State.audit_log_next_page,
        ),
        spacing="2",
        align="center",
    )


def _audit_log_tab_content() -> rx.Component:
    return rx.vstack(
        rx.text(
            "All auditable events (deletes, status changes, role changes) "
            "in this workspace.",
            size="2",
            color="var(--gray-10)",
        ),
        _audit_filter_bar(),
        rx.cond(
            State.audit_logs.length() > 0,
            rx.vstack(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("When"),
                            rx.table.column_header_cell("User"),
                            rx.table.column_header_cell("Action"),
                            rx.table.column_header_cell("Entity type"),
                            rx.table.column_header_cell("ID"),
                            rx.table.column_header_cell("Detail"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(State.audit_logs, _audit_log_row)
                    ),
                    width="100%",
                ),
                _audit_pagination(),
                spacing="3",
                align="start",
                width="100%",
            ),
            rx.box(
                rx.text(
                    "No audit log entries yet.",
                    size="2",
                    color="var(--gray-9)",
                ),
                padding_y="16px",
            ),
        ),
        spacing="4",
        align="start",
        width="100%",
    )


# ── Page root ──────────────────────────────────────────────────────────────────

def render_workspace_members() -> rx.Component:
    return rx.vstack(
        # Page header
        rx.vstack(
            rx.hstack(
                rx.icon("settings-2", size=22, color="var(--blue-9)"),
                rx.heading("Manage Workspace", size="6"),
                align="center",
                spacing="2",
            ),
            rx.text(
                "Configure settings and access for the ",
                rx.text.span(State.active_product_name, weight="bold"),
                " workspace.",
                size="2",
                color="var(--gray-10)",
            ),
            spacing="1",
            align="start",
        ),
        rx.separator(width="100%"),

        # Tabs
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Workspace Details", value="details"),
                rx.tabs.trigger("Members", value="members"),
                rx.tabs.trigger("Audit Log", value="audit"),
            ),
            rx.tabs.content(
                _workspace_details_tab_content(),
                value="details",
                padding_top="20px",
            ),
            rx.tabs.content(
                _members_tab_content(),
                value="members",
                padding_top="20px",
            ),
            rx.tabs.content(
                _audit_log_tab_content(),
                value="audit",
                padding_top="20px",
            ),
            default_value="details",
            width="100%",
        ),

        spacing="6",
        align="start",
        width="100%",
        max_width="960px",
        padding="32px",
    )
