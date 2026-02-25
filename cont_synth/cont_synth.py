import reflex as rx
from .state import State, LedgerItem, PersonaBadge, QuoteItem, InterviewHistoryItem

def render_persona_badge(badge: PersonaBadge):
    """Helper to render individual persona pills."""
    return rx.badge(badge.name, color_scheme=badge.color, variant="soft")

def render_quote(q: QuoteItem):
    """Renders a sleek card for an individual quote inside the modal."""
    return rx.card(
        rx.vstack(
            rx.badge(q.persona_name, color_scheme=q.persona_color, variant="soft", size="2"),
            rx.text(f'"{q.text}"', size="3", font_style="italic", color="var(--slate-11)"),
            spacing="3"
        ),
        size="2",
        width="100%",
        variant="surface",
        flex_shrink="0"  
    )

def show_ledger_row(item: LedgerItem):
    return rx.table.row(
        rx.table.cell(rx.badge(item.theme, color_scheme="gray", variant="solid")),
        rx.table.cell(rx.flex(rx.foreach(item.personas_affected, render_persona_badge), spacing="2", wrap="wrap")),
        rx.table.cell(
            rx.vstack(
                rx.text(item.opportunity),
                rx.cond(
                    item.is_cross_functional,
                    rx.badge("🌟 Cross-Persona Impact", color_scheme="amber", variant="soft", size="1"),
                    rx.fragment()
                ),
                spacing="1"
            )
        ),
        # --- THE NEW EVIDENCE BUTTON & MODAL ---
        rx.table.cell(
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.button(rx.icon("quote"), "Evidence", variant="soft", color_scheme="gray", size="1")
                ),
                rx.dialog.content(
                    rx.dialog.title("Supporting Evidence", margin_bottom="2"),
                    
                    # --- THE NEW POLISHED HEADER ---
                    rx.vstack(
                        rx.badge(item.theme, color_scheme="gray", variant="solid"),
                        rx.text(item.opportunity, weight="bold", size="4"),
                        spacing="2",
                        margin_bottom="12px"
                    ),
                    
                    # --- THE SCROLLABLE EVIDENCE LIST ---
                    rx.flex(
                        rx.foreach(item.evidence, render_quote),
                        direction="column",
                        spacing="4",
                        max_height="50vh", 
                        overflow_y="auto", 
                        padding_right="4",
                        width="100%" 
                    ),
                    
                    rx.flex(
                        rx.dialog.close(rx.button("Close", variant="soft", color_scheme="gray")),
                        justify="end",
                        margin_top="12px"
                    ),
                    max_width="650px" # Slightly wider to accommodate longer quotes
                )
            )
        ),
        rx.table.cell(rx.badge(item.status, color_scheme=item.status_color, variant="soft", size="2")),
        rx.table.cell(item.days_old),
        
        style=rx.cond(item.is_cross_functional, {"backgroundColor": "var(--amber-2)"}, {})
    )

def show_history_row(item: InterviewHistoryItem):
    return rx.table.row(
        rx.table.cell(item.interview_id, weight="bold"),
        rx.table.cell(rx.badge(item.persona, color_scheme="gray", variant="solid")),
        rx.table.cell(item.date_logged),
        rx.table.cell(rx.text(item.snippet, color="gray", size="2")),
        rx.table.cell(
            rx.button(
                rx.icon("trash", size=16), 
                "Delete", 
                color_scheme="red", 
                variant="soft", 
                on_click=lambda: State.delete_interview(item.interview_id)
            )
        )
    )

# --- SIDEBAR COMPONENT ---
def sidebar_item(text: str, icon: str, view_name: str) -> rx.Component:
    """Renders a sidebar navigation link that highlights softly when active."""
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(text, size="3", weight="medium"),
            spacing="3",
            align_items="center",
            width="100%", # <--- THE FIX: Force the internal stack to stretch fully
            justify="start" # <--- Align the contents of the stack to the left
        ),
        width="100%",
        padding_left="16px",
        variant=rx.cond(State.current_view == view_name, "soft", "ghost"),
        color_scheme=rx.cond(State.current_view == view_name, "blue", "gray"),
        on_click=State.set_current_view(view_name),
        size="3"
    )

def sidebar() -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.heading("The Catalyst", size="6", weight="bold"),
            rx.text("Continuous Discovery", color="gray", size="2"),
            spacing="1",
            margin_bottom="6"
        ),
        sidebar_item("Synthesize", "sparkles", "synthesize"),
        sidebar_item("Global Ledger", "table", "ledger"),
        sidebar_item("Pre-Meeting Prep", "target", "prep"),
        sidebar_item("Interview Logs", "archive", "logs"),
        
        width="300px",
        height="100vh",
        padding="24px",
        background_color="var(--gray-2)",
        border_right="1px solid var(--gray-5)",
        align_items="stretch"
    )

# --- VIEW COMPONENTS (Extracting your old tabs) ---
def render_synthesize() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Extract & Deduplicate.", weight="bold", size="6"),
            rx.text("Upload raw interview transcripts to extract unmet needs and merge them into the knowledge base.", color="gray", size="3"),
            margin_bottom="10px"
        ),
        rx.divider(),
        rx.input(placeholder="Persona (e.g., Consultant, MD)", value=State.persona_input, on_change=State.set_persona_input, width="100%", size="3", custom_attrs={"list": "persona-suggestions"}),
        rx.el.datalist(rx.foreach(State.available_personas, lambda p: rx.el.option(value=p)), id="persona-suggestions"),
        rx.upload(
            rx.vstack(rx.button("Select File", color_scheme="blue", variant="outline"), rx.text("Drag & Drop PDF/DOCX/TXT", color="gray"), align_items="center"),
            id="upload1", multiple=False, padding="20px", border="2px dashed #ccc", border_radius="8px", width="100%",
            on_drop=State.handle_upload(rx.upload_files(upload_id="upload1"))
        ),
        rx.text_area(placeholder="Transcript text...", value=State.transcript_text, on_change=State.set_transcript_text, min_height="300px", width="100%"),
        rx.button("Run Dual-Engine Synthesis", on_click=State.run_synthesis, loading=State.is_processing, size="4", width="100%", color_scheme="blue"),
        width="100%", max_width="900px", spacing="4", padding_top="20px"
    )

def render_ledger() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("The Single Source of Truth.", weight="bold", size="6"),
            rx.text("This ledger aggregates unmet needs across all personas, tracking the decay of our confidence over time.", color="gray", size="3"),
            margin_bottom="10px"
        ),
        rx.divider(),
        rx.button("Refresh Global Ledger", on_click=State.load_ledger, size="2", variant="outline"),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell("Theme"),
                rx.table.column_header_cell("Personas Affected"),
                rx.table.column_header_cell("Master Opportunity"),
                rx.table.column_header_cell("Evidence"),
                rx.table.column_header_cell("Status"),
                rx.table.column_header_cell("Days Since Validated"),
            )),
            rx.table.body(rx.foreach(State.ledger_data, show_ledger_row)),
            width="100%", variant="surface"
        ),
        width="100%", max_width="1400px", spacing="4", padding_top="20px"
    )

def render_prep() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Targeted Assumption Testing.", weight="bold", size="6"),
            rx.text("Select a persona to view your Battle Plan. Regenerate scripts when new evidence changes the landscape.", color="gray", size="3"),
            margin_bottom="10px"
        ),
        rx.divider(),
        
        # --- DROPDOWN WITH NEW ON_CHANGE HANDLER ---
        rx.select(
            State.available_personas, 
            value=State.target_persona, 
            on_change=State.load_prep_for_persona, # <--- CALLS THE DB LOADER
            size="3", 
            width="100%"
        ),
        
        # --- GENERATE BUTTON ---
        rx.button(
            # Change text dynamically based on whether we have a script or not
            rx.cond(
                State.prep_questions != "",
                "Regenerate Script (Overwrite)",
                "Generate New Script"
            ),
            on_click=State.generate_hostile_questions, 
            loading=State.is_prepping, 
            size="4", 
            width="100%", 
            color_scheme="red",
            variant=rx.cond(State.prep_questions != "", "outline", "solid") # Outline if it exists (safety), Solid if new
        ),
        
        # --- THE SCRIPT DISPLAY ---
        rx.cond(
            State.prep_questions != "", 
            rx.box(
                # Show the last updated timestamp
                rx.flex(
                    rx.badge("Battle Plan", color_scheme="red", variant="solid"),
                    rx.text(f"Last Updated: {State.prep_last_updated}", color="gray", size="1"),
                    justify="between",
                    align="center",
                    margin_bottom="10px"
                ),
                rx.markdown(State.prep_questions), 
                padding="20px", 
                background_color="var(--gray-3)", 
                border_radius="8px", 
                width="100%", 
                margin_top="20px"
            )
        ),
        width="100%", max_width="900px", spacing="4", padding_top="20px"
    )

def render_logs() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text("Raw Transcript Management.", weight="bold", size="6"),
            rx.text("View and delete ingested interviews to keep the Global Ledger clean.", color="gray", size="3"),
            margin_bottom="10px"
        ),
        rx.divider(),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell("ID"),
                rx.table.column_header_cell("Persona"),
                rx.table.column_header_cell("Date Logged"),
                rx.table.column_header_cell("Transcript Snippet"),
                rx.table.column_header_cell("Action"),
            )),
            rx.table.body(rx.foreach(State.interview_history, show_history_row)),
            width="100%", variant="surface"
        ),
        width="100%", max_width="1200px", spacing="4", padding_top="20px"
    )

# --- MAIN DASHBOARD LAYOUT ---
def index() -> rx.Component:
    return rx.hstack(
        sidebar(), # The new fixed sidebar on the left
        
        # The dynamic main content area on the right
        rx.box(
            rx.match(
                State.current_view,
                ("synthesize", render_synthesize()),
                ("ledger", render_ledger()),
                ("prep", render_prep()),
                ("logs", render_logs()),
                render_synthesize() # Default fallback
            ),
            padding="40px",
            width="100%",
            height="100vh",
            overflow_y="auto" # Allows scrolling only in the main content area
        ),
        width="100%",
        height="100vh",
        spacing="0",
        on_mount=State.load_ledger # Still loads the data when the app boots
    )

app = rx.App()
app.add_page(index)

app = rx.App()
app.add_page(index)