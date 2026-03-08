import reflex as rx
from cont_synth.state import State

# ── PRISMA brand palette (matches sidebar letter colors) ──────────────────────
_RED    = "#E5484D"
_AMBER  = "#E8A119"
_GREEN  = "#30A46C"
_BLUE   = "#0090FF"
_VIOLET = "#6E56CF"
_PINK   = "#E93D82"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prisma_wordmark(letter_size: str = "8") -> rx.Component:
    """Coloured PRISMA wordmark matching the sidebar branding."""
    return rx.hstack(
        rx.icon("triangle", size=36, color="var(--gray-12)"),
        rx.hstack(
            rx.text("P", color=_RED,    weight="bold", size=letter_size),
            rx.text("R", color=_AMBER,  weight="bold", size=letter_size),
            rx.text("I", color=_GREEN,  weight="bold", size=letter_size),
            rx.text("S", color=_BLUE,   weight="bold", size=letter_size),
            rx.text("M", color=_VIOLET, weight="bold", size=letter_size),
            rx.text("A", color=_PINK,   weight="bold", size=letter_size),
            spacing="1",
        ),
        spacing="3",
        align="center",
    )


def _section_label(text: str) -> rx.Component:
    return rx.text(
        text,
        size="1",
        weight="bold",
        color="var(--gray-9)",
        text_transform="uppercase",
        letter_spacing="0.08em",
    )


def _step_card(
    number: int,
    icon: str,
    title: str,
    desc: str,
    accent: str,
    bg: str,
) -> rx.Component:
    """One step in the discovery pipeline."""
    return rx.box(
        rx.vstack(
            # Number badge + icon
            rx.hstack(
                rx.box(
                    rx.text(
                        str(number),
                        size="1",
                        weight="bold",
                        color="white",
                        line_height="1",
                    ),
                    width="22px",
                    height="22px",
                    border_radius="50%",
                    background_color=accent,
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    flex_shrink="0",
                ),
                rx.icon(icon, size=16, color=accent),
                spacing="2",
                align="center",
            ),
            rx.text(title, size="3", weight="bold", color="var(--gray-12)"),
            rx.text(desc, size="2", color="var(--gray-11)", line_height="1.5"),
            spacing="2",
            align="start",
        ),
        padding="16px",
        background_color=bg,
        border_radius="10px",
        border="1px solid",
        border_color="var(--gray-5)",
        style={"boxShadow": f"inset 4px 0 0 {accent}"},
        flex="1",
        min_width="0",
    )


def _arrow_right() -> rx.Component:
    return rx.icon("arrow-right", size=18, color="var(--gray-8)", flex_shrink="0")


def _arrow_down() -> rx.Component:
    return rx.center(
        rx.icon("arrow-down", size=18, color="var(--gray-8)"),
        width="100%",
    )


def _feature_card(
    icon: str,
    title: str,
    desc: str,
    accent: str,
) -> rx.Component:
    """Supporting feature highlight card."""
    return rx.card(
        rx.vstack(
            rx.box(
                rx.icon(icon, size=20, color=accent),
                padding="8px",
                background_color="var(--gray-3)",
                border_radius="8px",
                width="fit-content",
            ),
            rx.text(title, size="3", weight="bold", color="var(--gray-12)"),
            rx.text(desc, size="2", color="var(--gray-11)", line_height="1.5"),
            spacing="3",
            align="start",
        ),
        width="100%",
        height="100%",
    )


# ── Sections ──────────────────────────────────────────────────────────────────

def _hero_section() -> rx.Component:
    return rx.vstack(
        _prisma_wordmark(letter_size="8"),
        rx.text(
            "Refract insights into action",
            size="5",
            color="var(--gray-11)",
            text_align="center",
        ),
        rx.box(
            rx.text(
                "PRISMA is a continuous product discovery platform that turns raw user "
                "interviews into a prioritised opportunity ledger — powered by Gemini AI "
                "and guided by the Continuous Discovery methodology.",
                size="3",
                color="var(--gray-11)",
                text_align="center",
                line_height="1.7",
            ),
            max_width="600px",
        ),
        spacing="4",
        align="center",
        width="100%",
        padding_y="24px",
    )


def _pipeline_section() -> rx.Component:
    """The six-step discovery loop, arranged as a circuit: 1→2→3 / 6←5←4."""
    return rx.vstack(
        # Section header
        rx.vstack(
            _section_label("The Discovery Loop"),
            rx.heading("How PRISMA works", size="5", weight="bold"),
            rx.text(
                "Six steps, one continuous cycle. Interview weekly. Insights compound.",
                size="3",
                color="var(--gray-11)",
            ),
            spacing="2",
            align="start",
        ),

        # Row 1: steps 1 → 2 → 3
        rx.hstack(
            _step_card(
                1, "file-text",
                "Upload Interview",
                "Paste or upload your raw interview transcript or notes. "
                "Any format works — PRISMA handles the rest.",
                _RED, "var(--red-2)",
            ),
            _arrow_right(),
            _step_card(
                2, "sparkles",
                "AI Synthesis",
                "Gemini 2.5-pro reads the transcript, extracts product "
                "opportunities, attaches evidence quotes, and deduplicates "
                "against your existing ledger.",
                _AMBER, "var(--amber-2)",
            ),
            _arrow_right(),
            _step_card(
                3, "circle-check",
                "Review & Confirm",
                "You're always in the loop. Inspect each AI finding, "
                "accept or discard, and confirm what belongs in your ledger.",
                _GREEN, "var(--green-2)",
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),

        # Connecting arrow pointing down-right (from step 3 → step 4)
        rx.hstack(
            rx.spacer(),
            rx.icon("corner-down-left", size=20, color="var(--gray-7)"),
            width="100%",
        ),

        # Row 2: steps 6 ← 5 ← 4 (reverse direction to form a loop)
        rx.hstack(
            _step_card(
                6, "refresh-cw",
                "Repeat Weekly",
                "Interview at least once a week. The coach tracks your "
                "technique over time. Insights compound into a rich, "
                "living picture of your customers.",
                _PINK, "var(--pink-2)",
            ),
            rx.icon("arrow-left", size=18, color="var(--gray-8)", flex_shrink="0"),
            _step_card(
                5, "flask-conical",
                "Experiment",
                "Attach solutions and experiments to each opportunity. "
                "Run Fake Door tests, A/B tests, or Prototype Interviews. "
                "Mark what's validated, invalidated, or shipped.",
                _VIOLET, "var(--violet-2)",
            ),
            rx.icon("arrow-left", size=18, color="var(--gray-8)", flex_shrink="0"),
            _step_card(
                4, "sliders",
                "Prioritise",
                "Score opportunities by Impact and Satisfaction Gap. "
                "The priority matrix surfaces your highest-leverage bets "
                "so you pick the right thing to build.",
                _BLUE, "var(--blue-2)",
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),

        spacing="4",
        width="100%",
    )


def _features_section() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            _section_label("Built-in Tools"),
            rx.heading("Everything your team needs", size="5", weight="bold"),
            spacing="2",
            align="start",
        ),
        rx.grid(
            _feature_card(
                "graduation-cap",
                "Interview Coach",
                "After every synthesis run, Gemini 2.5-flash scores your "
                "interview against the Mom Test methodology — tracking your "
                "keep-doing, stop-doing, and start-doing trends over time.",
                _VIOLET,
            ),
            _feature_card(
                "target",
                "Pre-Meeting Prep",
                "Generate tailored prep guides before each interview: "
                "open-ended questions, hypotheses to test, and relevant "
                "opportunities to probe — all generated from your own ledger.",
                _AMBER,
            ),
            _feature_card(
                "users",
                "Participants CRM",
                "Track every person you've spoken to: their persona, "
                "segment, recruitment source, and which interviews they "
                "appeared in. Distinguish customers from your own team.",
                _BLUE,
            ),
            _feature_card(
                "book-open",
                "Product Context",
                "Upload docs, specs, and research papers into a RAG "
                "knowledge base. The AI reads them before synthesising "
                "so its output is grounded in your product reality.",
                _GREEN,
            ),
            columns="2",
            gap="16px",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


def _philosophy_section() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.icon("quote", size=28, color="var(--gray-7)"),
            rx.text(
                (
                    "\u201cContinuous discovery is the practice of conducting at least one "
                    "touch point per week with a customer, with the goal of continuously "
                    "building out the opportunity space.\u201d"
                ),
                size="4",
                color="var(--gray-12)",
                text_align="center",
                line_height="1.7",
                font_style="italic",
            ),
            rx.text(
                "— Teresa Torres, Continuous Discovery Habits",
                size="2",
                color="var(--gray-10)",
                text_align="center",
            ),
            rx.divider(width="80px"),
            rx.text(
                "PRISMA is built around this idea. The sidebar, the coach, the cadence "
                "tracker — everything nudges your team toward that weekly rhythm.",
                size="3",
                color="var(--gray-11)",
                text_align="center",
                line_height="1.6",
            ),
            spacing="4",
            align="center",
        ),
        padding="32px",
        background_color="var(--gray-2)",
        border="1px solid var(--gray-5)",
        border_radius="12px",
        width="100%",
    )


def _data_model_section() -> rx.Component:
    """Visual summary of the data hierarchy."""
    def _node(label: str, color: str, icon_name: str) -> rx.Component:
        return rx.hstack(
            rx.box(
                rx.icon(icon_name, size=14, color=color),
                padding="6px",
                background_color="var(--gray-3)",
                border_radius="6px",
            ),
            rx.text(label, size="2", weight="medium", color="var(--gray-12)"),
            spacing="2",
            align="center",
            padding="8px 12px",
            border_radius="8px",
            border="1px solid var(--gray-5)",
            background_color="var(--gray-1)",
            width="fit-content",
        )

    def _connector(label: str = "") -> rx.Component:
        return rx.hstack(
            rx.box(width="32px", border_bottom="1px dashed var(--gray-6)"),
            rx.text(label, size="1", color="var(--gray-8)") if label else rx.fragment(),
            rx.box(width="32px", border_bottom="1px dashed var(--gray-6)"),
            align="center",
            spacing="1",
        ) if label else rx.box(
            border_left="1px dashed var(--gray-6)",
            height="16px",
            margin_left="22px",
        )

    return rx.vstack(
        rx.vstack(
            _section_label("Data Model"),
            rx.heading("How your data is structured", size="5", weight="bold"),
            rx.text(
                "Everything in PRISMA connects through a clear hierarchy from workspace to experiment.",
                size="3",
                color="var(--gray-11)",
            ),
            spacing="2",
            align="start",
        ),
        rx.card(
            rx.hstack(
                # Left column: main hierarchy
                rx.vstack(
                    _node("Workspace (Product)", _BLUE, "layers"),
                    rx.box(border_left="2px dashed var(--gray-5)", height="16px", margin_left="24px"),
                    _node("Outcome", _AMBER, "flag"),
                    rx.box(border_left="2px dashed var(--gray-5)", height="16px", margin_left="24px"),
                    _node("Opportunity", _RED, "lightbulb"),
                    rx.box(border_left="2px dashed var(--gray-5)", height="16px", margin_left="24px"),
                    _node("Solution", _GREEN, "wrench"),
                    rx.box(border_left="2px dashed var(--gray-5)", height="16px", margin_left="24px"),
                    _node("Experiment", _VIOLET, "flask-conical"),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                # Right column: linked entities
                rx.vstack(
                    rx.text("Also linked to Opportunities:", size="2", color="var(--gray-10)", weight="medium"),
                    rx.vstack(
                        _node("Interview", _AMBER, "archive"),
                        _node("Participant", _BLUE, "user"),
                        _node("Feedback / Coach", _VIOLET, "graduation-cap"),
                        _node("Knowledge Base Docs", _GREEN, "book-open"),
                        spacing="2",
                    ),
                    spacing="3",
                    align="start",
                    padding_top="8px",
                ),
                align="start",
                spacing="8",
                width="100%",
            ),
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ── Page root ─────────────────────────────────────────────────────────────────

def render_about() -> rx.Component:
    return rx.vstack(
        _hero_section(),
        rx.divider(),
        _pipeline_section(),
        rx.divider(),
        _features_section(),
        rx.divider(),
        _data_model_section(),
        rx.divider(),
        _philosophy_section(),
        # Footer nudge
        rx.center(
            rx.hstack(
                rx.text("Ready to start?", size="3", color="var(--gray-11)"),
                rx.button(
                    rx.icon("sparkles", size=14),
                    "Synthesize your first interview",
                    color_scheme="blue",
                    variant="solid",
                    size="2",
                    on_click=State.handle_navigation("synthesize"),
                ),
                spacing="3",
                align="center",
            ),
            width="100%",
            padding_y="8px",
        ),
        width="100%",
        max_width="960px",
        spacing="6",
        padding_top="20px",
        padding_bottom="40px",
        align="start",
    )
