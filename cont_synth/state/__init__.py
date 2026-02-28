import html as _html_module
import re as _re
import reflex as rx

from .core import (
    ExperimentItem,
    LlmUsageItem,
    OppDetailSolution,
    PersonaBadge,
    QuoteItem,
    SolutionItem,
    OutcomeItem,
    InterviewHistoryItem,
    LedgerItem,
    PersonaPrep,
    ProductItem,
    PendingOppItem,
    PendingLlmUsage,
)
from .auth import _hash_password, _verify_password
from ..models import User
from .navigation import NavigationStateMixin
from .interviews import InterviewStateMixin
from .ledger import LedgerStateMixin

_MARK_OPEN = '<mark style="background:rgba(250,204,21,0.5);border-radius:2px;padding:1px 2px">'
_MARK_CLOSE = "</mark>"


def _inject_mark(escaped: str, escaped_quote: str) -> str:
    """Wrap the first occurrence of escaped_quote in <mark> tags inside escaped.

    Pass 1 – exact substring match (fast path).
    Pass 2 – word-by-word regex that allows any whitespace (\\s+) between words,
              so quotes that span newline-separated sentences still match.
    """
    if not escaped_quote.strip():
        return escaped

    # --- Pass 1: exact ---
    idx = escaped.find(escaped_quote)
    if idx >= 0:
        end = idx + len(escaped_quote)
        return escaped[:idx] + _MARK_OPEN + escaped[idx:end] + _MARK_CLOSE + escaped[end:]

    # --- Pass 2: flexible whitespace ---
    words = escaped_quote.split()
    if len(words) < 2:
        return escaped
    pattern = r"\s+".join(_re.escape(w) for w in words)
    m = _re.search(pattern, escaped)
    if m:
        return escaped[:m.start()] + _MARK_OPEN + escaped[m.start():m.end()] + _MARK_CLOSE + escaped[m.end():]

    return escaped


class State(
    NavigationStateMixin,
    InterviewStateMixin,
    LedgerStateMixin,
    rx.State,
):
    """Main application state composed from feature-specific mixins."""

    # --- Authentication ---
    is_authenticated: bool = False
    auth_user_id: int = 0
    auth_username: str = ""
    auth_fullname: str = ""
    login_username: str = ""
    login_password: str = ""
    login_error: str = ""

    # --- Account settings ---
    is_settings_open: bool = False
    settings_username: str = ""
    settings_fullname: str = ""
    settings_new_password: str = ""
    settings_confirm_password: str = ""
    settings_error: str = ""
    settings_success: str = ""

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
    new_solution_status: str = "Ideation"
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
    is_editing_opp_detail: bool = False
    parent_opp_choices: list[str] = []

    # --- Evidence tracking ---
    interview_choices: list[str] = []
    selected_interview_choice: str = ""
    manual_quote_text: str = ""

    # --- Interview detail view ---
    selected_interview_id: int = 0
    interview_detail_persona: str = ""
    interview_detail_persona_color: str = "gray"
    interview_detail_date: str = ""
    interview_detail_transcript: str = ""
    interview_detail_quotes: list[QuoteItem] = []
    active_quote_index: int = 0

    # --- Pending synthesis (confirmation step) ---
    pending_synthesis_transcript: str = ""
    pending_synthesis_persona: str = ""
    pending_synthesis_quality: int = 0
    pending_synthesis_feedback: str = ""
    pending_synthesis_memorable_quote: str = ""
    pending_synthesis_opps: list[PendingOppItem] = []
    pending_llm_usages: list[PendingLlmUsage] = []

    # --- Shared highlight state (synthesis review + interview detail) ---
    highlighted_quote_text: str = ""
    # Incremented on every highlight request so Reflex always detects a state
    # change and executes the returned rx.call_script even when the quote text
    # hasn't changed (e.g. clicking the pre-selected first item).
    scroll_trigger: int = 0

    # --- Drawer tab control ---
    active_drawer_tab: str = "evidence"

    # --- Transcript drawer (from opportunity evidence cards) ---
    transcript_drawer_open: bool = False
    transcript_drawer_mode: str = "view"           # "view" | "select"
    transcript_drawer_interview_id: int = -1
    transcript_drawer_transcript: str = ""
    transcript_drawer_persona: str = ""
    transcript_drawer_persona_color: str = ""
    transcript_drawer_date: str = ""
    transcript_drawer_selection: str = ""          # JS-captured text selection
    transcript_drawer_opportunity_id: int = -1     # target opp when in select mode

    # --- LLM Usage dashboard ---
    llm_usage_logs: list[LlmUsageItem] = []
    workspace_menu_open: bool = False

    # --- Experiments workspace ---
    experiment_target_solution_id: int = -1
    experiment_target_solution_name: str = ""
    selected_solution_for_experiment: str = ""
    new_experiment_name: str = ""
    new_experiment_assumption: str = ""
    new_experiment_method: str = "Prototype Interview"
    editing_experiment_id: int = -1

    @rx.var
    def active_product_name(self) -> str:
        """Display name for the currently selected workspace."""
        active = next((p for p in self.products if str(p.id) == self.active_product_id), None)
        return active.name if active else "Select workspace"

    @rx.var
    def llm_total_tokens(self) -> int:
        return sum(log.total_tokens for log in self.llm_usage_logs)

    @rx.var
    def llm_synthesis_count(self) -> int:
        return sum(1 for log in self.llm_usage_logs if log.operation == "synthesis")

    @rx.var
    def llm_dedupe_count(self) -> int:
        return sum(1 for log in self.llm_usage_logs if log.operation == "dedupe")

    def toggle_workspace_menu(self):
        self.workspace_menu_open = not self.workspace_menu_open

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def login(self):
        """Verify credentials and authenticate the user."""
        from sqlmodel import select as _select
        username = self.login_username.strip()
        password = self.login_password
        if not username or not password:
            self.login_error = "Please enter your username and password."
            return
        with rx.session() as session:
            user = session.exec(_select(User).where(User.username == username)).first()
        if not user or not _verify_password(password, user.password_hash):
            self.login_error = "Invalid username or password."
            return
        self.auth_user_id = user.id
        self.auth_username = user.username
        self.auth_fullname = user.fullname
        self.is_authenticated = True
        self.login_error = ""
        self.login_username = ""
        self.login_password = ""
        yield rx.call_script(f"localStorage.setItem('auth_user_id', '{user.id}')")
        self.load_data_for_current_view()
        yield rx.call_script(
            "localStorage.getItem('active_product_id') || ''",
            callback=State.restore_product_from_storage,
        )

    def logout(self):
        """Clear the session and return to the login screen."""
        self.is_authenticated = False
        self.auth_user_id = 0
        self.auth_username = ""
        self.auth_fullname = ""
        return rx.call_script("localStorage.removeItem('auth_user_id')")

    def verify_stored_session(self, stored_id: str):
        """Callback from localStorage on app mount — restores session if valid."""
        if not stored_id or not stored_id.strip().isdigit():
            return
        user_id = int(stored_id.strip())
        with rx.session() as session:
            user = session.get(User, user_id)
        if not user:
            return
        self.auth_user_id = user.id
        self.auth_username = user.username
        self.auth_fullname = user.fullname
        self.is_authenticated = True
        self.load_data_for_current_view()
        return rx.call_script(
            "localStorage.getItem('active_product_id') || ''",
            callback=State.restore_product_from_storage,
        )

    def handle_login_key(self, key: str):
        """Submit login on Enter key press."""
        if key == "Enter":
            yield State.login()

    def open_account_settings(self):
        """Open the account settings modal pre-filled with current user data."""
        self.settings_username = self.auth_username
        self.settings_fullname = self.auth_fullname
        self.settings_new_password = ""
        self.settings_confirm_password = ""
        self.settings_error = ""
        self.settings_success = ""
        self.is_settings_open = True

    def close_account_settings(self):
        """Close the account settings modal and clear its form."""
        self.is_settings_open = False
        self.settings_username = ""
        self.settings_fullname = ""
        self.settings_new_password = ""
        self.settings_confirm_password = ""
        self.settings_error = ""
        self.settings_success = ""

    def save_account_settings(self):
        """Persist updated profile and optional new password to the database."""
        from sqlmodel import select as _select
        self.settings_error = ""
        self.settings_success = ""
        new_username = self.settings_username.strip()
        new_fullname = self.settings_fullname.strip()
        if not new_username or not new_fullname:
            self.settings_error = "Username and full name are required."
            return
        if self.settings_new_password or self.settings_confirm_password:
            if self.settings_new_password != self.settings_confirm_password:
                self.settings_error = "Passwords do not match."
                return
            if len(self.settings_new_password) < 6:
                self.settings_error = "Password must be at least 6 characters."
                return
        with rx.session() as session:
            user = session.get(User, self.auth_user_id)
            if not user:
                self.settings_error = "User not found."
                return
            if new_username != user.username:
                existing = session.exec(
                    _select(User).where(User.username == new_username)
                ).first()
                if existing:
                    self.settings_error = "That username is already taken."
                    return
            user.username = new_username
            user.fullname = new_fullname
            if self.settings_new_password:
                user.password_hash = _hash_password(self.settings_new_password)
            session.add(user)
            session.commit()
        self.auth_username = new_username
        self.auth_fullname = new_fullname
        self.settings_new_password = ""
        self.settings_confirm_password = ""
        self.settings_success = "Settings saved successfully."

    def load_app(self):
        """Initial app load — check auth first; data loads only after session is verified."""
        return rx.call_script(
            "localStorage.getItem('auth_user_id') || ''",
            callback=State.verify_stored_session,
        )

    def restore_product_from_storage(self, stored_id: str):
        """Applies the localStorage-persisted workspace if it still exists."""
        if stored_id and any(str(p.id) == stored_id for p in self.products):
            if self.active_product_id != stored_id:
                self.active_product_id = stored_id
                self.load_data_for_current_view()

    async def capture_drawer_selection(self):
        """On mouseup in the transcript box, capture the browser text selection via JS."""
        yield rx.call_script(
            "window.getSelection().toString()",
            callback=State.set_drawer_selection,
        )

    @rx.var
    def active_quote(self) -> QuoteItem:
        if not self.interview_detail_quotes:
            return QuoteItem(interview_id=0, persona_name="", persona_color="gray", text="No evidence snippets found.")
        idx = max(0, min(self.active_quote_index, len(self.interview_detail_quotes) - 1))
        return self.interview_detail_quotes[idx]

    @rx.var
    def has_prev_quote(self) -> bool:
        return self.active_quote_index > 0

    @rx.var
    def has_next_quote(self) -> bool:
        return self.active_quote_index < len(self.interview_detail_quotes) - 1

    @rx.var
    def quote_position(self) -> str:
        if not self.interview_detail_quotes:
            return "0 of 0"
        return f"{self.active_quote_index + 1} of {len(self.interview_detail_quotes)}"

    @rx.var
    def selected_opp_count(self) -> int:
        return sum(1 for opp in self.pending_synthesis_opps if opp.selected)

    @rx.var
    def detail_transcript_html(self) -> str:
        """Interview detail transcript with the active quote highlighted in yellow."""
        escaped = _inject_mark(
            _html_module.escape(self.interview_detail_transcript),
            _html_module.escape(self.highlighted_quote_text),
        )
        return f'<div style="white-space:pre-wrap;font-family:inherit;font-size:14px;line-height:1.6;color:var(--gray-12)">{escaped}</div>'

    @rx.var
    def synthesis_review_transcript_html(self) -> str:
        """Pending transcript with the clicked evidence quote highlighted in yellow."""
        escaped = _inject_mark(
            _html_module.escape(self.pending_synthesis_transcript),
            _html_module.escape(self.highlighted_quote_text),
        )
        return f'<div style="white-space:pre-wrap;font-family:inherit;font-size:14px;line-height:1.6;color:var(--gray-12)">{escaped}</div>'

    @rx.var
    def transcript_drawer_html(self) -> str:
        """Drawer transcript with the active quote highlighted in yellow."""
        escaped = _inject_mark(
            _html_module.escape(self.transcript_drawer_transcript),
            _html_module.escape(self.highlighted_quote_text),
        )
        return f'<div style="white-space:pre-wrap;font-family:inherit;font-size:14px;line-height:1.6;color:var(--gray-12)">{escaped}</div>'

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
    "LlmUsageItem",
    "OppDetailSolution",
    "PersonaBadge",
    "QuoteItem",
    "SolutionItem",
    "OutcomeItem",
    "InterviewHistoryItem",
    "LedgerItem",
    "PersonaPrep",
    "PendingOppItem",
]
