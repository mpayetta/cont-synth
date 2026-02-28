import reflex as rx
from cont_synth.state import State


def login_page() -> rx.Component:
    """Full-screen centered login form. Shown when the user is not authenticated."""
    return rx.center(
        rx.card(
            rx.vstack(
                # Header
                rx.vstack(
                    rx.heading("The Catalyst", size="7", weight="bold", text_align="center"),
                    rx.text(
                        "Continuous Discovery",
                        size="2",
                        color="var(--gray-9)",
                        text_align="center",
                    ),
                    spacing="1",
                    align="center",
                    margin_bottom="6",
                ),
                # Username field
                rx.vstack(
                    rx.text("Username", size="2", weight="medium"),
                    rx.input(
                        placeholder="Enter your username",
                        value=State.login_username,
                        on_change=State.set_login_username,
                        width="100%",
                        size="3",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Password field
                rx.vstack(
                    rx.text("Password", size="2", weight="medium"),
                    rx.input(
                        placeholder="Enter your password",
                        type="password",
                        value=State.login_password,
                        on_change=State.set_login_password,
                        on_key_down=State.handle_login_key,
                        width="100%",
                        size="3",
                    ),
                    spacing="1",
                    width="100%",
                ),
                # Error message
                rx.cond(
                    State.login_error != "",
                    rx.callout.root(
                        rx.callout.icon(rx.icon("triangle-alert", size=16)),
                        rx.callout.text(State.login_error, size="2"),
                        color_scheme="red",
                        variant="soft",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                # Sign in button
                rx.button(
                    "Sign In",
                    on_click=State.login,
                    width="100%",
                    size="3",
                    color_scheme="blue",
                ),
                spacing="4",
                width="100%",
            ),
            width="360px",
            padding="32px",
        ),
        width="100%",
        height="100vh",
        background_color="var(--gray-2)",
    )
