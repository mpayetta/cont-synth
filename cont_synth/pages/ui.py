"""Shared UI components."""
import reflex as rx
from cont_synth.state import State

_COMBO_INPUT_STYLE = {
    "width": "100%",
    "padding": "0 36px 0 12px",
    "height": "36px",
    "border": "1px solid var(--gray-6)",
    "border_radius": "6px",
    "background": "var(--color-surface)",
    "color": "var(--gray-12)",
    "font_size": "14px",
    "box_sizing": "border-box",
    "outline": "none",
    "_focus": {
        "border_color": "var(--blue-8)",
        "box_shadow": "0 0 0 1px var(--blue-8)",
    },
}


def combo_box(
    placeholder: str,
    value,
    on_change,
    field_id: str,
    suggestions,
    input_style: dict | None = None,
) -> rx.Component:
    """Combobox: shows a dropdown list of suggestions while allowing free-form entry.

    Args:
        placeholder: Input placeholder text.
        value: Reactive state var holding the current value.
        on_change: Event handler called on every keystroke.
        field_id: Unique string identifying this combobox (used to track open state).
        suggestions: Reactive list of filtered suggestions to show.
        input_style: Optional CSS overrides for the input element.
    """
    merged_style = {**_COMBO_INPUT_STYLE, **(input_style or {})}
    is_open = State.open_combo == field_id

    return rx.box(
        # ── Click-away overlay ─────────────────────────────────────────────────
        rx.cond(
            is_open,
            rx.box(
                on_click=State.close_combo_box,
                position="fixed",
                top="0",
                left="0",
                right="0",
                bottom="0",
                z_index="9",
            ),
        ),
        # ── Input + chevron ────────────────────────────────────────────────────
        rx.box(
            rx.el.input(
                placeholder=placeholder,
                value=value,
                on_change=on_change,
                on_focus=State.open_combo_box(field_id),
                style=merged_style,
            ),
            rx.icon(
                "chevron-down",
                size=14,
                on_click=State.open_combo_box(field_id),
                position="absolute",
                right="10px",
                top="50%",
                transform="translateY(-50%)",
                color="var(--gray-9)",
                cursor="pointer",
            ),
            position="relative",
            width="100%",
        ),
        # ── Suggestion dropdown ────────────────────────────────────────────────
        rx.cond(
            is_open,
            rx.cond(
                suggestions.length() > 0,
                rx.box(
                    rx.foreach(
                        suggestions,
                        lambda opt: rx.box(
                            rx.text(opt, size="2"),
                            on_click=State.select_combo_option(field_id, opt),
                            padding="6px 12px",
                            cursor="pointer",
                            border_radius="4px",
                            _hover={"background": "var(--gray-3)"},
                        ),
                    ),
                    position="absolute",
                    top="calc(100% + 4px)",
                    left="0",
                    right="0",
                    background="var(--color-panel-solid)",
                    border="1px solid var(--gray-6)",
                    border_radius="8px",
                    box_shadow="0 4px 16px rgba(0,0,0,0.18)",
                    z_index="10",
                    max_height="220px",
                    overflow_y="auto",
                    padding="4px",
                ),
            ),
        ),
        position="relative",
        width="100%",
        z_index="1",
    )
