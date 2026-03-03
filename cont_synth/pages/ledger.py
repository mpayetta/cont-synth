import reflex as rx
from cont_synth.state import (
    State,
    LedgerItem,
    PersonaBadge,
    ThemeGroup,
    BoardColumn,
    MatrixCell,
)


# --- HELPER COMPONENTS ---
def render_persona_badge(badge: PersonaBadge):
    """Helper to render individual persona pills."""
    return rx.badge(badge.name, color_scheme=badge.color, variant="soft")



def _info_label(text, explanation: str) -> rx.Component:
    """A label + clickable ? icon that opens a popover with an explanation."""
    return rx.flex(
        rx.text(text, size="2", color="var(--gray-12)", weight="medium"),
        rx.popover.root(
            rx.popover.trigger(
                rx.icon(
                    "circle-help",
                    size=14,
                    color="var(--gray-12)",
                    cursor="pointer",
                    _hover={"color": "var(--gray-12)"},
                ),
            ),
            rx.popover.content(
                rx.text(explanation, size="2"),
                max_width="280px",
                side="top",
            ),
        ),
        spacing="1",
        align="center",
    )


def _score_dot(item: LedgerItem, field: str, score: int) -> rx.Component:
    """A single clickable dot for the 1-5 score selector."""
    score_var = item.impact_score if field == "impact" else item.sat_gap_score
    is_filled = score_var >= score
    return rx.box(
        width="10px",
        height="10px",
        border_radius="50%",
        background_color=rx.cond(
            is_filled,
            rx.cond(field == "impact", "var(--blue-9)", "var(--violet-9)"),
            "var(--gray-4)",
        ),
        cursor="pointer",
        flex_shrink="0",
        on_click=lambda: State.update_opp_score(item.opportunity_id, field, str(score)),
        _hover={
            "background_color": rx.cond(
                field == "impact", "var(--blue-7)", "var(--violet-7)"
            )
        },
        transition="background-color 0.1s ease",
    )


def show_ledger_row(item: LedgerItem):
    """Renders a single opportunity as a card with Torres scoring and experiment status."""
    priority_color = rx.cond(
        item.priority_score >= 11, "green",
        rx.cond(item.priority_score >= 6, "amber",
            rx.cond(item.priority_score >= 1, "blue", "gray")),
    )

    return rx.box(
        rx.box(
        rx.vstack(
            # ── Row 1: badges + right-side status chips ──────────────────
            rx.flex(
                # Left: indent arrow + theme + tags
                rx.flex(
                    rx.cond(
                        item.indent_level > 0,
                        rx.icon("corner-down-right", size=13, color="var(--gray-12)"),
                        rx.fragment(),
                    ),
                    rx.cond(
                        item.is_target,
                        rx.badge(
                            rx.icon("crosshair", size=10),
                            "Target",
                            color_scheme="green", variant="solid", size="1",
                        ),
                        rx.fragment(),
                    ),
                    rx.badge(item.theme, color_scheme="gray", variant="solid", size="1"),
                    rx.cond(
                        item.is_cross_functional,
                        rx.badge("Cross-Persona", color_scheme="amber", variant="soft", size="1"),
                        rx.fragment(),
                    ),
                    spacing="2", align="center", flex="1",
                ),
                # Right: running experiments + priority score + target toggle
                rx.flex(
                    # Running experiments pill (only shown when > 0)
                    rx.cond(
                        item.running_experiments > 0,
                        rx.badge(
                            rx.icon("flask-conical", size=10),
                            f"{item.running_experiments} running",
                            color_scheme="orange", variant="soft", size="1",
                        ),
                        rx.fragment(),
                    ),
                    # Priority score badge
                    rx.badge(
                        f"P: {item.priority_score}",
                        color_scheme=priority_color,
                        variant=rx.cond(item.priority_score > 0, "soft", "outline"),
                        size="1",
                        title="Priority = Impact + Satisfaction Gap + Frequency (evidence count)",
                    ),
                    # Target toggle button
                    rx.icon_button(
                        rx.cond(
                            item.is_target,
                            rx.icon("crosshair", size=12),
                            rx.icon("crosshair", size=12),
                        ),
                        size="1",
                        variant=rx.cond(item.is_target, "solid", "ghost"),
                        color_scheme=rx.cond(item.is_target, "green", "gray"),
                        title=rx.cond(item.is_target, "Remove target designation", "Set as target opportunity"),
                        on_click=lambda: State.set_target_opportunity(item.opportunity_id),
                    ),
                    spacing="2", align="center", flex_shrink="0",
                ),
                justify="between", width="100%", align="center",
            ),
            # ── Row 2: Opportunity statement (hero text, 2-line clamp) ───
            rx.text(
                item.opportunity,
                weight="bold",
                size="4",
                line_height="1.4",
                cursor="pointer",
                on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
                _hover={"color": "var(--blue-11)"},
                transition="color 0.1s ease",
                style={
                    "overflow": "hidden",
                    "display": "-webkit-box",
                    "-webkit-line-clamp": "2",
                    "-webkit-box-orient": "vertical",
                },
            ),
            # ── Row 3: Personas + quick metrics ──────────────────────────
            rx.flex(
                rx.flex(
                    rx.foreach(
                        item.personas_affected,
                        lambda b: rx.badge(b.name, color_scheme=b.color, variant="soft", size="1"),
                    ),
                    spacing="1", wrap="wrap",
                ),
                rx.flex(
                    rx.flex(
                        rx.icon("quote", size=11, color="var(--gray-12)"),
                        rx.text(f"{item.evidence.length()} quotes", size="1", color="var(--gray-12)"),
                        spacing="1", align="center",
                    ),
                    rx.text("·", size="1", color="var(--gray-6)"),
                    rx.flex(
                        rx.icon("lightbulb", size=11, color="var(--gray-12)"),
                        rx.text(f"{item.solutions.length()} solutions", size="1", color="var(--gray-12)"),
                        spacing="1", align="center",
                    ),
                    rx.text("·", size="1", color="var(--gray-6)"),
                    rx.text(
                        f"{item.days_old}d",
                        size="1",
                        weight="medium",
                        color=rx.cond(
                            item.status_color == "green", "var(--green-9)",
                            rx.cond(item.status_color == "yellow", "var(--amber-9)", "var(--red-9)"),
                        ),
                        title=item.status,
                    ),
                    spacing="2", align="center",
                ),
                justify="between", width="100%", align="center",
            ),
            # ── Row 4: Compact Torres scoring (single row) ───────────────
            rx.flex(
                _info_label("Impact", "Impact (1–5): How much does solving this opportunity move your target business outcome? 5 = critical driver, 1 = marginal effect."),
                rx.flex(
                    _score_dot(item, "impact", 1),
                    _score_dot(item, "impact", 2),
                    _score_dot(item, "impact", 3),
                    _score_dot(item, "impact", 4),
                    _score_dot(item, "impact", 5),
                    spacing="1", align="center",
                ),
                rx.box(width="1px", height="12px", background_color="var(--gray-6)", flex_shrink="0", margin_x="2"),
                _info_label("Gap", "Satisfaction Gap (1–5): How unhappy are users with the current situation? 5 = severe pain / no workaround, 1 = mild annoyance. High gap means users urgently want a better solution."),
                rx.flex(
                    _score_dot(item, "sat_gap", 1),
                    _score_dot(item, "sat_gap", 2),
                    _score_dot(item, "sat_gap", 3),
                    _score_dot(item, "sat_gap", 4),
                    _score_dot(item, "sat_gap", 5),
                    spacing="1", align="center",
                ),
                rx.box(width="1px", height="12px", background_color="var(--gray-6)", flex_shrink="0", margin_x="2"),
                _info_label(f"Freq {item.evidence.length()}/5", "Frequency: How many interviews mentioned this opportunity (auto-counted from linked quotes, capped at 5). Combined with Impact and Gap to form the Priority score: Impact + Gap + Freq (max 15)."),
                spacing="2", align="center", flex_wrap="wrap",
            ),
            spacing="3",
            width="100%",
            align_items="start",
        ),
        padding="16px 16px 14px 20px",
        border_left=rx.cond(
            item.is_target,
            "4px solid var(--green-8)",
            rx.cond(
                item.status_color == "green", "4px solid var(--green-6)",
                rx.cond(item.status_color == "yellow", "4px solid var(--amber-6)", "4px solid var(--red-6)"),
            ),
        ),
        border_radius="8px",
        background_color=rx.cond(
            item.is_target,
            "var(--green-1)",
            rx.cond(
                item.priority_score >= 11,
                "var(--amber-1)",
                rx.cond(
                    item.priority_score >= 6,
                    "var(--blue-1)",
                    rx.cond(item.indent_level > 0, "var(--gray-2)", "var(--gray-1)"),
                ),
            ),
        ),
        border="1px solid var(--gray-4)",
        width="100%",
        _hover={
            "background_color": rx.cond(item.is_target, "var(--green-2)", "var(--blue-1)"),
            "border_color": rx.cond(item.is_target, "var(--green-6)", "var(--blue-5)"),
        },
        transition="background-color 0.1s ease, border-color 0.1s ease",
    ),
    padding_left=f"calc({item.indent_level} * 28px)",
    width="100%",
    )


# ── THEME-GROUPED LIST VIEW ───────────────────────────────────────────────────

def show_theme_group(group: ThemeGroup) -> rx.Component:
    """Renders a collapsible group of opportunities sharing the same theme."""
    priority_color = rx.cond(
        group.avg_priority >= 11, "amber",
        rx.cond(group.avg_priority >= 6, "blue", "gray"),
    )
    return rx.vstack(
        # Group header (click to collapse/expand)
        rx.flex(
            rx.flex(
                rx.icon(
                    rx.cond(group.collapsed, "chevron-right", "chevron-down"),
                    size=14, color="var(--gray-12)",
                ),
                rx.cond(
                    group.is_target_group,
                    rx.icon("crosshair", size=12, color="var(--green-9)"),
                    rx.fragment(),
                ),
                rx.text(group.theme, weight="bold", size="3"),
                rx.badge(
                    f"{group.count}",
                    color_scheme="gray", variant="surface", size="1",
                ),
                spacing="2", align="center",
            ),
            rx.badge(
                f"avg P:{group.avg_priority}",
                color_scheme=priority_color, variant="soft", size="1",
            ),
            justify="between",
            width="100%",
            cursor="pointer",
            on_click=lambda: State.toggle_theme_collapse(group.theme),
            padding="8px 14px",
            border_radius="6px",
            background_color="var(--gray-3)",
            border="1px solid var(--gray-5)",
            _hover={"background_color": "var(--gray-4)"},
            transition="background-color 0.1s ease",
        ),
        # Items — hidden when collapsed
        rx.cond(
            group.collapsed,
            rx.fragment(),
            rx.vstack(
                rx.foreach(group.opps, show_ledger_row),
                spacing="2",
                width="100%",
                padding_left="8px",
            ),
        ),
        spacing="2",
        width="100%",
    )


# ── BOARD / KANBAN VIEW ───────────────────────────────────────────────────────

def show_board_card(item: LedgerItem) -> rx.Component:
    """A compact card for the Kanban board view."""
    return rx.box(
        rx.vstack(
            # Theme badge + priority score
            rx.flex(
                rx.badge(item.theme, color_scheme="gray", variant="solid", size="1"),
                rx.flex(
                    rx.cond(
                        item.running_experiments > 0,
                        rx.badge(
                            rx.icon("flask-conical", size=9),
                            color_scheme="orange", variant="soft", size="1",
                        ),
                        rx.fragment(),
                    ),
                    rx.cond(
                        item.is_target,
                        rx.icon("crosshair", size=11, color="var(--green-9)"),
                        rx.fragment(),
                    ),
                    spacing="1", align="center",
                ),
                justify="between", width="100%", align="center",
            ),
            # Statement (2-line clamp)
            rx.text(
                item.opportunity,
                size="2",
                weight="medium",
                cursor="pointer",
                on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
                _hover={"color": "var(--blue-11)"},
                style={
                    "overflow": "hidden",
                    "display": "-webkit-box",
                    "-webkit-line-clamp": "3",
                    "-webkit-box-orient": "vertical",
                },
            ),
            # Persona badges
            rx.flex(
                rx.foreach(
                    item.personas_affected,
                    lambda b: rx.badge(b.name, color_scheme=b.color, variant="soft", size="1"),
                ),
                spacing="1", wrap="wrap",
            ),
            # Quick metrics
            rx.flex(
                rx.icon("quote", size=10, color="var(--gray-12)"),
                rx.text(f"{item.evidence.length()}", size="1", color="var(--gray-12)"),
                rx.text("·", size="1", color="var(--gray-5)"),
                rx.icon("lightbulb", size=10, color="var(--gray-12)"),
                rx.text(f"{item.solutions.length()}", size="1", color="var(--gray-12)"),
                rx.text("·", size="1", color="var(--gray-5)"),
                rx.text(
                    f"{item.days_old}d",
                    size="1",
                    color=rx.cond(
                        item.status_color == "green", "var(--green-9)",
                        rx.cond(item.status_color == "yellow", "var(--amber-9)", "var(--red-9)"),
                    ),
                ),
                spacing="1", align="center",
            ),
            spacing="2",
        ),
        padding="12px",
        border_radius="8px",
        border_left=rx.cond(
            item.is_target,
            "3px solid var(--green-8)",
            rx.cond(
                item.status_color == "green", "3px solid var(--green-6)",
                rx.cond(item.status_color == "yellow", "3px solid var(--amber-6)", "3px solid var(--red-6)"),
            ),
        ),
        background_color=rx.cond(
            item.is_target, "var(--green-1)",
            rx.cond(
                item.priority_score >= 8, "var(--amber-1)",
                "var(--gray-1)",
            ),
        ),
        border="1px solid var(--gray-4)",
        width="100%",
        cursor="pointer",
        on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
        _hover={"border_color": "var(--blue-5)", "background_color": "var(--blue-1)"},
        transition="background-color 0.1s ease, border-color 0.1s ease",
    )


def show_board_column(col: BoardColumn) -> rx.Component:
    """One priority-tier column in the Kanban board."""
    return rx.vstack(
        rx.flex(
            rx.badge(col.label, color_scheme=col.color, variant="soft", size="2"),
            rx.text(f"{col.opps.length()}", size="1", color="var(--gray-12)"),
            spacing="2", align="center", justify="between", width="100%",
        ),
        rx.scroll_area(
            rx.vstack(
                rx.foreach(col.opps, show_board_card),
                spacing="2",
                width="100%",
            ),
            max_height="calc(100vh - 260px)",
            width="100%",
        ),
        width="280px",
        flex_shrink="0",
        spacing="3",
    )


def show_board_view() -> rx.Component:
    """Kanban board: 4 columns by priority tier (High / Medium / Low / Unscored)."""
    return rx.scroll_area(
        rx.flex(
            rx.foreach(State.ledger_board_columns, show_board_column),
            spacing="4",
            align="start",
            width="max-content",
            min_width="100%",
        ),
        overflow_x="auto",
        width="100%",
    )


# ── PRIORITY MATRIX VIEW ──────────────────────────────────────────────────────

def show_matrix_cell(cell: MatrixCell) -> rx.Component:
    """One cell in the 5×5 Impact × Sat-Gap priority matrix."""
    return rx.box(
        rx.vstack(
            rx.foreach(
                cell.opps,
                lambda item: rx.box(
                    rx.text(
                        item.theme,
                        size="1",
                        weight="bold",
                        color=rx.cond(item.is_target, "var(--green-11)", "var(--blue-11)"),
                        overflow="hidden",
                        white_space="nowrap",
                        text_overflow="ellipsis",
                        max_width="100%",
                    ),
                    rx.text(
                        item.opportunity,
                        size="1",
                        color="var(--gray-12)",
                        style={
                            "overflow": "hidden",
                            "display": "-webkit-box",
                            "-webkit-line-clamp": "2",
                            "-webkit-box-orient": "vertical",
                        },
                    ),
                    padding="4px 6px",
                    border_radius="4px",
                    background_color=rx.cond(item.is_target, "var(--green-3)", "var(--blue-3)"),
                    border="1px solid",
                    border_color=rx.cond(item.is_target, "var(--green-6)", "var(--blue-5)"),
                    cursor="pointer",
                    width="100%",
                    on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
                    _hover={"opacity": "0.8"},
                ),
            ),
            spacing="1",
        ),
        min_height="70px",
        padding="6px",
        background_color=rx.cond(
            cell.is_sweet_spot, "var(--green-2)", "var(--gray-1)"
        ),
        border="1px solid",
        border_color=rx.cond(
            cell.is_sweet_spot, "var(--green-4)", "var(--gray-4)"
        ),
        border_radius="4px",
        overflow="hidden",
        width="100%",
    )


def show_matrix_view() -> rx.Component:
    """5×5 Impact × Satisfaction Gap priority matrix."""
    return rx.vstack(
        # Axis guide + legend
        rx.vstack(
            rx.flex(
                rx.text(
                    "Priority = Impact + Satisfaction Gap + Frequency  (max 15)",
                    size="2", weight="bold", color="var(--gray-12)",
                ),
                rx.flex(
                    rx.box(width="12px", height="12px", background_color="var(--green-3)",
                           border="1px solid var(--green-5)", border_radius="2px", flex_shrink="0"),
                    rx.text("Priority zone", size="1", color="var(--gray-12)"),
                    spacing="1", align="center",
                ),
                justify="between", width="100%", align="center",
            ),
            rx.flex(
                rx.flex(
                    rx.text("X-axis — ", size="1", color="var(--gray-12)", weight="medium"),
                    rx.text(
                        "Impact (1–5):",
                        size="1", color="var(--gray-12)", weight="bold",
                    ),
                    rx.text(
                        " How much does solving this move your business outcome?",
                        size="1", color="var(--gray-12)",
                    ),
                    spacing="1", align="center",
                ),
                rx.text("·", size="1", color="var(--gray-5)"),
                rx.flex(
                    rx.text("Y-axis — ", size="1", color="var(--gray-12)", weight="medium"),
                    rx.text(
                        "Sat. Gap (1–5):",
                        size="1", color="var(--gray-12)", weight="bold",
                    ),
                    rx.text(
                        " How unhappy are users with the current situation? (5 = severe pain)",
                        size="1", color="var(--gray-12)",
                    ),
                    spacing="1", align="center",
                ),
                spacing="2", align="center", flex_wrap="wrap",
            ),
            spacing="1",
            width="100%",
        ),
        # Column headers (impact 1→5)
        rx.flex(
            rx.box(width="32px", flex_shrink="0"),  # gutter for row labels
            rx.grid(
                rx.text("I:1", size="1", color="var(--gray-12)", text_align="center"),
                rx.text("I:2", size="1", color="var(--gray-12)", text_align="center"),
                rx.text("I:3", size="1", color="var(--gray-12)", text_align="center"),
                rx.text("I:4", size="1", color="var(--gray-12)", text_align="center"),
                rx.text("I:5", size="1", color="var(--gray-12)", text_align="center"),
                columns="5",
                width="100%",
                spacing="1",
            ),
            align="center",
            spacing="1",
            width="100%",
        ),
        # Row labels + matrix grid
        rx.flex(
            # Y-axis labels (sat_gap 5→1, top to bottom)
            rx.vstack(
                rx.text("G:5", size="1", color="var(--gray-12)", width="32px", text_align="center"),
                rx.text("G:4", size="1", color="var(--gray-12)", width="32px", text_align="center"),
                rx.text("G:3", size="1", color="var(--gray-12)", width="32px", text_align="center"),
                rx.text("G:2", size="1", color="var(--gray-12)", width="32px", text_align="center"),
                rx.text("G:1", size="1", color="var(--gray-12)", width="32px", text_align="center"),
                justify="between",
                height="350px",
                flex_shrink="0",
            ),
            rx.grid(
                rx.foreach(State.matrix_cells, show_matrix_cell),
                columns="5",
                spacing="1",
                width="100%",
            ),
            spacing="1",
            align="start",
            width="100%",
        ),
        # Unscored opportunities (need rating before appearing in matrix)
        rx.cond(
            State.matrix_unscored.length() > 0,
            rx.vstack(
                rx.flex(
                    rx.icon("alert-circle", size=14, color="var(--amber-9)"),
                    rx.text("Needs scoring", size="2", weight="bold", color="var(--amber-11)"),
                    rx.text(
                        "— click to open and set Impact + Sat. Gap scores so these appear in the matrix",
                        size="2", color="var(--gray-12)",
                    ),
                    spacing="2", align="center",
                ),
                rx.flex(
                    rx.foreach(
                        State.matrix_unscored,
                        lambda item: rx.badge(
                            item.theme + " · " + item.opportunity,
                            color_scheme="gray",
                            variant="outline",
                            size="1",
                            cursor="pointer",
                            on_click=lambda: State.navigate_to_opportunity(item.opportunity_id),
                            style={
                                "overflow": "hidden",
                                "max-width": "220px",
                                "text-overflow": "ellipsis",
                                "white-space": "nowrap",
                            },
                        ),
                    ),
                    wrap="wrap",
                    spacing="2",
                ),
                spacing="3",
                padding_top="20px",
                width="100%",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="3",
    )

def render_ledger() -> rx.Component:
    """The main view for the Global Ledger."""
    return rx.vstack(
        # --- NEW OUTCOME HEADER ---
        rx.flex(
            rx.box(
                rx.text("Opportunities List", weight="bold", size="6"),
                rx.text(
                    "Filter by business outcome to focus your Continuous Discovery efforts.",
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
                    rx.dialog.trigger(
                        rx.button("+ New Outcome", variant="soft", size="3")
                    ),
                    rx.dialog.content(
                        rx.dialog.title("Define Business Outcome"),
                        rx.dialog.description(
                            "What metric are we trying to move?", margin_bottom="8px"
                        ),
                        rx.input(
                            placeholder="e.g., Increase Q3 Retention",
                            default_value=State.new_outcome_name,
                            on_blur=State.set_new_outcome_name,
                            margin_bottom="12px",
                        ),
                        rx.flex(
                            rx.dialog.close(
                                rx.button("Cancel", variant="soft", color_scheme="gray")
                            ),
                            rx.dialog.close(
                                rx.button(
                                    "Save Outcome",
                                    on_click=State.create_outcome,
                                    color_scheme="blue",
                                )
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
        # --- Action Bar: New Opportunity + View Mode Toggle ---
        rx.flex(
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button(
                        "+ New Opportunity",
                        size="2",
                        color_scheme="blue",
                        variant="soft",
                        on_click=State.open_opp_dialog,
                    )
                ),
                rx.dialog.content(
                    rx.dialog.title(
                        rx.cond(
                            State.editing_opp_id != -1,
                            "Edit Opportunity",
                            "Create Manual Opportunity",
                        )
                    ),
                    rx.dialog.description(
                        "Manually add or update an opportunity.", margin_bottom="8px"
                    ),
                    rx.vstack(
                        rx.text("Parent Opportunity", size="2", weight="bold"),
                        rx.select(
                            State.parent_opp_choices,
                            value=State.manual_opp_parent_id,
                            on_change=State.set_manual_opp_parent_id,
                            width="100%",
                        ),
                        rx.text("Theme / Category", size="2", weight="bold"),
                        rx.input(
                            placeholder="e.g., Usability, Pricing...",
                            default_value=State.manual_opp_theme,
                            on_blur=State.set_manual_opp_theme,
                            width="100%",
                        ),
                        rx.text(
                            "Opportunity Statement",
                            size="2",
                            weight="bold",
                            margin_top="2",
                        ),
                        rx.text_area(
                            placeholder="I need a way to...",
                            default_value=State.manual_opp_statement,
                            on_blur=State.set_manual_opp_statement,
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                        margin_bottom="12px",
                    ),
                    rx.flex(
                        rx.button(
                            "Cancel",
                            variant="soft",
                            color_scheme="gray",
                            on_click=State.close_opp_dialog,
                        ),
                        rx.button(
                            "Save Opportunity",
                            on_click=State.save_manual_opportunity,
                            color_scheme="blue",
                        ),
                        spacing="3",
                        justify="end",
                    ),
                    max_width="500px",
                ),
                open=State.is_opp_dialog_open,
                on_open_change=State.handle_opp_dialog_change,
            ),
            # View mode toggle buttons
            rx.flex(
                rx.button(
                    rx.icon("list", size=14),
                    "List",
                    variant=rx.cond(State.ledger_view_mode == "list", "solid", "outline"),
                    color_scheme="blue",
                    size="2",
                    on_click=State.set_ledger_view_mode("list"),
                ),
                rx.button(
                    rx.icon("columns-3", size=14),
                    "Board",
                    variant=rx.cond(State.ledger_view_mode == "board", "solid", "outline"),
                    color_scheme="blue",
                    size="2",
                    on_click=State.set_ledger_view_mode("board"),
                ),
                rx.button(
                    rx.icon("grid-2x2", size=14),
                    "Matrix",
                    variant=rx.cond(State.ledger_view_mode == "matrix", "solid", "outline"),
                    color_scheme="blue",
                    size="2",
                    on_click=State.set_ledger_view_mode("matrix"),
                ),
                gap="4px",
                align="center",
            ),
            justify="between",
            width="100%",
            align="center",
            margin_bottom="4",
        ),
        # --- Main Content (view-mode conditional) ---
        rx.cond(
            State.ledger_data.length() == 0,
            rx.center(
                rx.vstack(
                    rx.icon("inbox", size=36, color="var(--gray-12)"),
                    rx.text("No opportunities found.", weight="medium", color="gray"),
                    rx.text(
                        "Create one with the button above, or run a synthesis from an interview.",
                        size="2", color="gray", text_align="center",
                    ),
                    spacing="2", align="center",
                ),
                padding_y="80px",
                width="100%",
            ),
            rx.cond(
                State.ledger_view_mode == "board",
                show_board_view(),
                rx.cond(
                    State.ledger_view_mode == "matrix",
                    show_matrix_view(),
                    # Default: grouped list view
                    rx.vstack(
                        rx.foreach(State.ledger_data_by_theme, show_theme_group),
                        spacing="3",
                        width="100%",
                    ),
                ),
            ),
        ),
        width="100%",
        max_width="1400px",
        spacing="4",
        padding_top="20px",
    )
