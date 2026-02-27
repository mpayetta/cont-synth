import reflex as rx

from .core import (
    ExperimentItem,
    PersonaBadge,
    QuoteItem,
    SolutionItem,
    OutcomeItem,
    InterviewHistoryItem,
    LedgerItem,
    PersonaPrep,
    ProductItem,
)
from .navigation import NavigationStateMixin
from .interviews import InterviewStateMixin
from .ledger import LedgerStateMixin


class State(
    NavigationStateMixin,
    InterviewStateMixin,
    LedgerStateMixin,
    rx.State,
):
    """Main application state composed from feature-specific mixins."""

    # --- Navigation ---
    current_view: str = "synthesize"

    # --- Products ---
    products: list[ProductItem] = []
    active_product_id: str = "1"
    new_product_name: str = ""
    edit_product_name: str = ""

    # --- Interview & prep state ---
    is_processing: bool = False
    is_prepping: bool = False
    persona_input: str = ""
    transcript_text: str = ""
    prep_questions: str = ""
    prep_last_updated: str = ""

    interview_history: list[InterviewHistoryItem] = []

    # --- Ledger & personas ---
    is_drawer_open: bool = False
    ledger_data: list[LedgerItem] = []
    available_personas: list[str] = []
    target_persona: str = ""

    # --- Solutions workspace ---
    is_generating_solutions: bool = False
    new_solution_name: str = ""
    new_solution_desc: str = ""
    target_parent_name: str = ""
    editing_solution_id: int = -1
    target_parent_id: int = -1

    # --- Outcomes ---
    outcomes: list[OutcomeItem] = []
    outcome_names: list[str] = ["All Outcomes"]
    active_outcome_name: str = "All Outcomes"
    new_outcome_name: str = ""
    selected_opp_outcome_name: str = ""

    # --- Opportunity CRUD state ---
    editing_opp_id: int = -1
    manual_opp_theme: str = "Uncategorized"
    manual_opp_statement: str = ""
    manual_opp_parent_id: str = "None"
    is_opp_dialog_open: bool = False
    parent_opp_choices: list[str] = []

    # --- Evidence tracking ---
    interview_choices: list[str] = []
    selected_interview_choice: str = ""
    manual_quote_text: str = ""
    
    # --- Drawer tab control ---
    active_drawer_tab: str = "evidence"

    # --- Experiments workspace ---
    experiment_target_solution_id: int = -1
    experiment_target_solution_name: str = ""
    selected_solution_for_experiment: str = ""
    new_experiment_name: str = ""
    new_experiment_assumption: str = ""
    new_experiment_method: str = "Prototype Interview"
    editing_experiment_id: int = -1

    # Initialize with a blank dummy object so the frontend never hits a null crash
    selected_opportunity: LedgerItem = LedgerItem(
        opportunity_id=0,
        theme="",
        personas_affected=[],
        opportunity="",
        status="",
        status_color="gray",
        days_old=0,
        is_cross_functional=False,
        evidence=[],
        solutions=[],
        linked_outcomes=[],
    )


__all__ = [
    "State",
    "ExperimentItem",
    "PersonaBadge",
    "QuoteItem",
    "SolutionItem",
    "OutcomeItem",
    "InterviewHistoryItem",
    "LedgerItem",
    "PersonaPrep",
]
