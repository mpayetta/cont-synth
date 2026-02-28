import reflex as rx
from cont_synth.state import State


def account_settings_modal() -> rx.Component:
    """Dialog for updating the logged-in user's profile and password."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Account Settings"),
            rx.dialog.description(
                "Update your username, display name, or password.",
                size="2",
                color="var(--gray-9)",
                margin_bottom="4",
            ),
            rx.vstack(
                # Username
                rx.vstack(
                    rx.text("Username", size="2", weight="medium"),
                    rx.input(
                        value=State.settings_username,
                        on_change=State.set_settings_username,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Full name
                rx.vstack(
                    rx.text("Full Name", size="2", weight="medium"),
                    rx.input(
                        value=State.settings_fullname,
                        on_change=State.set_settings_fullname,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Divider
                rx.divider(),
                rx.text(
                    "Change Password",
                    size="2",
                    weight="medium",
                    color="var(--gray-11)",
                ),
                rx.text(
                    "Leave blank to keep your current password.",
                    size="1",
                    color="var(--gray-9)",
                    margin_top="-8px",
                ),
                # New password
                rx.vstack(
                    rx.text("New Password", size="2", weight="medium"),
                    rx.input(
                        type="password",
                        placeholder="New password (min. 6 characters)",
                        value=State.settings_new_password,
                        on_change=State.set_settings_new_password,
                        width="100%",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Confirm password
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
                    width="100%",
                ),
                # Error message
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
                # Success message
                rx.cond(
                    State.settings_success != "",
                    rx.callout.root(
                        rx.callout.icon(rx.icon("check-circle", size=16)),
                        rx.callout.text(State.settings_success, size="2"),
                        color_scheme="green",
                        variant="soft",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="3",
                width="100%",
            ),
            # Action buttons
            rx.flex(
                rx.button(
                    "Cancel",
                    variant="soft",
                    color_scheme="gray",
                    on_click=State.close_account_settings,
                ),
                rx.button(
                    "Save Changes",
                    on_click=State.save_account_settings,
                    color_scheme="blue",
                ),
                spacing="3",
                justify="end",
                margin_top="16px",
            ),
            max_width="440px",
        ),
        open=State.is_settings_open,
        on_open_change=State.set_is_settings_open,
    )
