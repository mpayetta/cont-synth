import html as _html_module
import re as _re
import reflex as rx
from sqlmodel import select

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
    ThemeGroup,
    BoardColumn,
    MatrixCell,
    PersonaPrep,
    ProductItem,
    PendingOppItem,
    PendingLlmUsage,
    ParticipantItem,
    PendingParticipantItem,
    DetailParticipantItem,
    DashboardBarItem,
    RecentInterviewItem,
    PrepOppItem,
    PrepExperimentItem,
    configure_genai,
)
from .auth import _hash_password, _verify_password
from ..models import (
    User,
    Experiment,
    InterviewParticipantLink,
    InterviewOpportunityLink,
    OutcomeOpportunityLink,
    LlmUsageLog,
    Interview,
    Solution,
    Opportunity,
    Outcome,
    Participant,
    Persona,
    Product,
)
from .navigation import NavigationStateMixin
from .interviews import InterviewStateMixin
from .ledger import LedgerStateMixin
from .participants import ParticipantStateMixin

_MARK_OPEN = '<mark style="background:rgba(250,204,21,0.5);border-radius:2px;padding:1px 2px">'
_MARK_CLOSE = "</mark>"


def _first_sentence(text: str) -> str:
    """Return the first meaningful chunk of text.

    Priority:
    1. Split on '...' (LLM-added ellipsis joining non-adjacent transcript lines).
    2. Split on a sentence-ending punctuation followed by whitespace.
    Falls back to the full text when no boundary is found.
    """
    # LLM often writes "sentence one... sentence two" when the two sentences
    # belong to different speaker turns. Matching only the first part is enough
    # to locate and scroll to the right spot.
    ellipsis = _re.search(r'\.\.\.+', text)
    if ellipsis and ellipsis.start() > 10:
        return text[:ellipsis.start()].rstrip()

    # Sentence boundary: punctuation followed by whitespace
    m = _re.search(r'[.?!]\s', text)
    if m and m.start() > 10:
        return text[:m.start() + 1]  # include the punctuation, drop the space

    return text


def _find_span(escaped: str, fragment: str, after: int = 0) -> tuple[int, int] | None:
    """Return (start, end) of the first match of fragment in escaped[after:], or None.

    Case-insensitive exact substring first, then flexible-whitespace word regex.
    """
    if not fragment.strip():
        return None
    search_area = escaped[after:]
    idx = search_area.lower().find(fragment.lower())
    if idx >= 0:
        return (after + idx, after + idx + len(fragment))
    words = fragment.split()
    if len(words) >= 2:
        pattern = r"\s+".join(_re.escape(w) for w in words)
        m = _re.search(pattern, search_area, _re.IGNORECASE)
        if m:
            return (after + m.start(), after + m.end())
    return None


def _mark_fragment(escaped: str, fragment: str) -> str | None:
    """Try to wrap fragment in <mark> inside escaped. Returns marked string or None."""
    span = _find_span(escaped, fragment)
    if span is None:
        return None
    s, e = span
    return escaped[:s] + _MARK_OPEN + escaped[s:e] + _MARK_CLOSE + escaped[e:]


def _inject_mark(escaped: str, escaped_quote: str) -> str:
    """Wrap the first occurrence of escaped_quote in <mark> tags inside escaped.

    Pass 1 – full quote (case-insensitive exact + flexible-whitespace regex).
    Pass 2 – each individual segment split by '...' tried in order; the first
              match wins. Handles the common LLM pattern of stitching
              non-adjacent transcript lines with ellipses when the surrounding
              text uses a plain '.' or newline instead.
    Pass 3 – first sentence of the quote only, as a last-resort anchor.
    Pass 4 – prefix anchor + suffix anchor. Finds where the quote starts (first
              N words, 7→4) and where it ends (last M words, searched after the
              prefix), then marks the entire span between them — covering all
              text between the two anchors even across speaker-attribution lines.
    """
    if not escaped_quote.strip():
        return escaped

    # Pass 1: try the full quote
    result = _mark_fragment(escaped, escaped_quote)
    if result is not None:
        return result

    # Pass 2: try each ellipsis-delimited segment individually (longest first)
    segments = [s.strip() for s in _re.split(r'\s*\.\.\.+\s*', escaped_quote)]
    for seg in sorted(segments, key=len, reverse=True):
        if len(seg) > 10:
            result = _mark_fragment(escaped, seg)
            if result is not None:
                return result

    # Pass 3: first sentence of the full quote as a final anchor
    first = _first_sentence(escaped_quote)
    if first != escaped_quote:
        result = _mark_fragment(escaped, first)
        if result is not None:
            return result

    # Pass 4: prefix anchor + suffix anchor → mark the full span between them.
    # Handles cross-turn quotes where the LLM joined non-adjacent speaker turns
    # without an ellipsis separator. We find where the quote starts (first N words)
    # and where it ends (last M words, searched only after the prefix match), then
    # highlight everything in between — including any speaker attribution text that
    # separates the two turns.
    words = escaped_quote.split()
    for n in range(min(7, len(words)), 3, -1):
        start_span = _find_span(escaped, " ".join(words[:n]))
        if start_span is None:
            continue
        # Found start; try to extend the mark to the end of the quote.
        end_span = start_span
        for m in range(min(7, len(words)), 3, -1):
            maybe = _find_span(escaped, " ".join(words[-m:]), after=start_span[1])
            if maybe is not None:
                end_span = maybe
                break
        s, e = start_span[0], end_span[1]
        return escaped[:s] + _MARK_OPEN + escaped[s:e] + _MARK_CLOSE + escaped[e:]

    return escaped


class State(
    NavigationStateMixin,
    InterviewStateMixin,
    LedgerStateMixin,
    ParticipantStateMixin,
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
    account_section: str = "settings"
    settings_username: str = ""
    settings_fullname: str = ""
    settings_gemini_api_key: str = ""
    show_api_key: bool = False
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
    synthesis_error: str = ""
    prep_questions: str = ""
    prep_last_updated: str = ""
    prep_extra_context: str = ""

    # --- Interview guide prep (OST-based) ---
    prep_opportunities: list[PrepOppItem] = []
    prep_running_experiments: list[PrepExperimentItem] = []

    interview_history: list[InterviewHistoryItem] = []

    # --- Ledger & personas ---
    ledger_data: list[LedgerItem] = []
    available_personas: list[str] = []
    target_persona: str = ""
    ledger_view_mode: str = "list"   # "list" | "board" | "matrix"
    collapsed_themes: list[str] = []

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

    # --- Merge opportunity state ---
    is_merge_dialog_open: bool = False
    merge_source_opp_id: int = -1
    merge_target_opp_id: int = -1
    merge_keep_statement: str = "target"  # "source" | "target"
    merge_keep_theme: str = "target"      # "source" | "target"

    # --- Evidence tracking ---
    interview_choices: list[str] = []
    selected_interview_choice: str = ""
    manual_quote_text: str = ""

    # --- Interview detail view ---
    selected_interview_id: int = 0
    selected_opportunity_id: int = 0
    interview_detail_persona: str = ""
    interview_detail_persona_color: str = "gray"
    interview_detail_date: str = ""
    interview_detail_transcript: str = ""
    interview_detail_quotes: list[QuoteItem] = []
    active_quote_index: int = 0
    # Extracted metadata (empty/0 = not available)
    interview_detail_interview_date: str = ""
    interview_detail_duration: int = 0
    interview_detail_participants: str = ""  # comma-joined display string
    interview_detail_participant_items: list[DetailParticipantItem] = []

    # --- Pending synthesis (confirmation step) ---
    pending_synthesis_transcript: str = ""
    pending_synthesis_persona: str = ""
    pending_synthesis_quality: int = 0
    pending_synthesis_feedback: str = ""
    pending_synthesis_memorable_quote: str = ""
    pending_synthesis_opps: list[PendingOppItem] = []
    pending_llm_usages: list[PendingLlmUsage] = []
    # Extracted interview metadata (all optional — empty/0 means not found)
    pending_synthesis_duration: int = 0        # 0 = not found
    pending_synthesis_interview_date: str = "" # "" = not found
    pending_synthesis_participants: list[str] = []
    # Parallel list of roles for each participant ("interviewee" or "interviewer")
    pending_synthesis_participant_roles: list[str] = []

    # --- Shared highlight state (synthesis review + interview detail) ---
    highlighted_quote_text: str = ""
    # Incremented on every highlight request so Reflex always detects a state
    # change and executes the returned rx.call_script even when the quote text
    # hasn't changed (e.g. clicking the pre-selected first item).
    scroll_trigger: int = 0

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

    # --- Participant CRM ---
    participants: list[ParticipantItem] = []
    participant_segments: list[str] = []
    participant_recruited_vias: list[str] = []
    show_team_members: bool = False
    is_participant_form_open: bool = False
    editing_participant_id: int = -1
    participant_form_name: str = ""
    participant_form_persona: str = ""
    participant_form_is_team_member: bool = False
    participant_form_segment: str = ""
    participant_form_recruited_via: str = ""
    participant_form_notes: str = ""

    # --- Experiments workspace ---
    experiment_target_solution_id: int = -1
    experiment_target_solution_name: str = ""
    selected_solution_for_experiment: str = ""
    new_experiment_name: str = ""
    new_experiment_assumption: str = ""
    new_experiment_description: str = ""
    new_experiment_success_metric: str = ""
    new_experiment_method: str = "Prototype Interview"
    new_experiment_method_other: str = ""
    editing_experiment_id: int = -1

    # --- Home dashboard ---
    dashboard_days_since_last: int = -1       # -1 = no interviews yet
    dashboard_total_interviews: int = 0
    dashboard_weekly_bars: list[DashboardBarItem] = []
    dashboard_exp_draft: int = 0
    dashboard_exp_running: int = 0
    dashboard_exp_concluded: int = 0
    dashboard_exp_validated: int = 0
    dashboard_exp_invalidated: int = 0
    dashboard_opps_with_evidence: int = 0
    dashboard_opps_with_solutions: int = 0
    dashboard_solutions_testing: int = 0
    dashboard_total_opps: int = 0
    dashboard_recent_interviews: list[RecentInterviewItem] = []

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

    def set_login_username(self, val: str): self.login_username = val
    def set_login_password(self, val: str): self.login_password = val

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
        configure_genai(user.gemini_api_key or "")
        yield rx.call_script(f"localStorage.setItem('auth_user_id', '{user.id}')")
        yield rx.call_script(
            "localStorage.getItem('active_product_id') || ''",
            callback=State.restore_product_from_storage,
        )
        yield rx.redirect("/")

    def logout(self):
        """Clear the session and return to the login screen."""
        self.is_authenticated = False
        self.auth_user_id = 0
        self.auth_username = ""
        self.auth_fullname = ""
        yield rx.call_script("localStorage.removeItem('auth_user_id')")
        yield rx.redirect("/login")

    def verify_stored_session(self, stored_id: str):
        """Callback from localStorage on app mount — restores session if valid."""
        if not stored_id or not stored_id.strip().isdigit():
            if self.router.page.path != "/login":
                return rx.redirect("/login")
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
        configure_genai(user.gemini_api_key or "")
        self.load_data_for_current_view()
        return rx.call_script(
            "localStorage.getItem('active_product_id') || ''",
            callback=State.restore_product_from_storage,
        )

    def handle_login_key(self, key: str):
        """Submit login on Enter key press."""
        if key == "Enter":
            yield State.login()

    # Explicit setters (replaces deprecated auto-setters)
    def set_account_section(self, val: str): self.account_section = val
    def set_settings_username(self, val: str): self.settings_username = val
    def set_settings_fullname(self, val: str): self.settings_fullname = val
    def set_settings_gemini_api_key(self, val: str): self.settings_gemini_api_key = val
    def set_settings_new_password(self, val: str): self.settings_new_password = val
    def set_settings_confirm_password(self, val: str): self.settings_confirm_password = val
    def set_new_product_name(self, val: str): self.new_product_name = val
    def set_edit_product_name(self, val: str): self.edit_product_name = val
    def set_persona_input(self, val: str): self.persona_input = val
    def set_transcript_text(self, val: str): self.transcript_text = val
    def set_prep_extra_context(self, val: str): self.prep_extra_context = val
    def set_ledger_view_mode(self, val: str): self.ledger_view_mode = val
    def set_new_solution_name(self, val: str): self.new_solution_name = val
    def set_new_solution_desc(self, val: str): self.new_solution_desc = val
    def set_new_solution_status(self, val: str): self.new_solution_status = val
    def set_new_outcome_name(self, val: str): self.new_outcome_name = val
    def set_manual_opp_theme(self, val: str): self.manual_opp_theme = val
    def set_manual_opp_statement(self, val: str): self.manual_opp_statement = val
    def set_manual_opp_parent_id(self, val: str): self.manual_opp_parent_id = val
    def set_selected_interview_choice(self, val: str): self.selected_interview_choice = val
    def set_participant_form_name(self, val: str): self.participant_form_name = val
    def set_participant_form_persona(self, val: str): self.participant_form_persona = val
    def set_participant_form_is_team_member(self, val: bool): self.participant_form_is_team_member = val
    def set_participant_form_segment(self, val: str): self.participant_form_segment = val
    def set_participant_form_recruited_via(self, val: str): self.participant_form_recruited_via = val
    def set_participant_form_notes(self, val: str): self.participant_form_notes = val
    def set_new_experiment_name(self, val: str): self.new_experiment_name = val
    def set_new_experiment_assumption(self, val: str): self.new_experiment_assumption = val
    def set_new_experiment_description(self, val: str): self.new_experiment_description = val
    def set_new_experiment_success_metric(self, val: str): self.new_experiment_success_metric = val
    def set_new_experiment_method(self, val: str): self.new_experiment_method = val
    def set_new_experiment_method_other(self, val: str): self.new_experiment_method_other = val

    def load_account_page(self):
        """On-mount handler for the /account page: pre-fill settings and load LLM usage."""
        self.current_view = "account"
        self.account_section = "settings"
        return self._ensure_auth_and_load()

    def _prefill_account_settings(self):
        """Pre-fill account settings form fields from the current user record."""
        with rx.session() as session:
            user = session.get(User, self.auth_user_id)
            if user:
                self.settings_gemini_api_key = user.gemini_api_key or ""
        self.settings_username = self.auth_username
        self.settings_fullname = self.auth_fullname
        self.settings_new_password = ""
        self.settings_confirm_password = ""
        self.settings_error = ""
        self.settings_success = ""
        self.show_api_key = False

    def toggle_show_api_key(self):
        """Toggle visibility of the Gemini API key input."""
        self.show_api_key = not self.show_api_key

    def save_account_settings(self):
        """Persist updated profile, API key, and optional new password to the database."""
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
        new_api_key = self.settings_gemini_api_key.strip()
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
            user.gemini_api_key = new_api_key if new_api_key else None
            if self.settings_new_password:
                user.password_hash = _hash_password(self.settings_new_password)
            session.add(user)
            session.commit()
        self.auth_username = new_username
        self.auth_fullname = new_fullname
        self.settings_gemini_api_key = new_api_key
        configure_genai(new_api_key)
        self.settings_new_password = ""
        self.settings_confirm_password = ""
        self.settings_success = "Settings saved successfully."

    def wipe_database(self):
        """Delete all data except the current user. Useful for resetting test state."""
        with rx.session() as session:
            # Delete in FK-safe order (children before parents)
            for row in session.exec(select(Experiment)).all():
                session.delete(row)
            for row in session.exec(select(InterviewParticipantLink)).all():
                session.delete(row)
            for row in session.exec(select(InterviewOpportunityLink)).all():
                session.delete(row)
            for row in session.exec(select(OutcomeOpportunityLink)).all():
                session.delete(row)
            for row in session.exec(select(LlmUsageLog)).all():
                session.delete(row)
            for row in session.exec(select(PersonaPrep)).all():  # PersonaPrep is from .core
                session.delete(row)
            for row in session.exec(select(Interview)).all():
                session.delete(row)
            # Solutions have a self-referential parent_id — clear children first
            for row in session.exec(select(Solution).where(Solution.parent_id != None)).all():
                session.delete(row)
            for row in session.exec(select(Solution)).all():
                session.delete(row)
            # Opportunities have a self-referential parent_id — clear children first
            for row in session.exec(select(Opportunity).where(Opportunity.parent_id != None)).all():
                session.delete(row)
            for row in session.exec(select(Opportunity)).all():
                session.delete(row)
            for row in session.exec(select(Outcome)).all():
                session.delete(row)
            for row in session.exec(select(Participant)).all():
                session.delete(row)
            for row in session.exec(select(Persona)).all():
                session.delete(row)
            for row in session.exec(select(Product)).all():
                session.delete(row)
            session.commit()

        # Reset all volatile state and return to the start
        self.current_view = "synthesize"
        self.interview_history = []
        self.ledger_data = []
        self.available_personas = []
        self.participants = []
        self.llm_usage_logs = []
        self.outcomes = []
        self.outcome_names = ["All Outcomes"]
        self.active_outcome_name = "All Outcomes"
        self.pending_synthesis_opps = []
        self.pending_synthesis_participants = []
        self.pending_synthesis_participant_roles = []
        self.prep_opportunities = []
        self.prep_running_experiments = []
        self.active_product_id = "1"
        return rx.redirect("/synthesize")

    def toggle_show_team_members(self):
        """Toggle visibility of product-team interviewers in the Participants table."""
        self.show_team_members = not self.show_team_members

    def _ensure_auth_and_load(self):
        """If already authenticated, load data for the current view.
        Otherwise trigger the localStorage auth check."""
        if self.is_authenticated:
            self.load_data_for_current_view()
        else:
            return rx.call_script(
                "localStorage.getItem('auth_user_id') || ''",
                callback=State.verify_stored_session,
            )

    # --- Per-page on_mount handlers ---

    def load_home_page(self):
        self.current_view = "home"
        return self._ensure_auth_and_load()

    def load_synthesize_page(self):
        self.current_view = "synthesize"
        return self._ensure_auth_and_load()

    def load_review_page(self):
        self.current_view = "synthesis_review"
        return self._ensure_auth_and_load()

    def load_ledger_page(self):
        self.current_view = "ledger"
        return self._ensure_auth_and_load()

    def load_opportunity_page(self):
        self.current_view = "opportunity"
        id_str = self.router.page.params.get("opportunity_id", "0")
        parsed_id = int(id_str) if id_str.isdigit() else 0
        if parsed_id > 0:
            self.selected_opportunity_id = parsed_id
        return self._ensure_auth_and_load()

    def load_interviews_page(self):
        self.current_view = "logs"
        return self._ensure_auth_and_load()

    def load_interview_detail_page(self):
        self.current_view = "interview_detail"
        id_str = self.router.page.params.get("interview_id", "0")
        parsed_id = int(id_str) if id_str.isdigit() else 0
        if parsed_id > 0:
            self.selected_interview_id = parsed_id
        # If params are empty (production client-side navigation timing issue),
        # keep the value already set by open_interview_detail().
        return self._ensure_auth_and_load()

    def load_prep_page(self):
        self.current_view = "prep"
        return self._ensure_auth_and_load()

    def load_participants_page(self):
        self.current_view = "participants"
        return self._ensure_auth_and_load()

    def load_llm_usage_page(self):
        self.current_view = "llm_usage"
        return self._ensure_auth_and_load()

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
    def pending_synthesis_participants_str(self) -> str:
        return ", ".join(self.pending_synthesis_participants)

    @rx.var
    def pending_participants_with_roles(self) -> list[PendingParticipantItem]:
        """Zips participant names with their current roles for the role-editor UI."""
        roles = self.pending_synthesis_participant_roles
        return [
            PendingParticipantItem(
                index=i,
                name=name,
                role=roles[i] if i < len(roles) else "interviewee",
            )
            for i, name in enumerate(self.pending_synthesis_participants)
        ]

    @rx.var
    def filtered_participants(self) -> list[ParticipantItem]:
        """Participants list filtered by the show_team_members toggle."""
        if self.show_team_members:
            return self.participants
        return [p for p in self.participants if not p.is_team_member]

    @rx.var
    def prep_persona_options(self) -> list[str]:
        """Persona list with a leading 'None' sentinel for the prep page dropdown."""
        return ["— None —"] + self.available_personas

    @rx.var
    def selected_opportunity_ids(self) -> list[int]:
        """IDs of opportunities checked in the prep page selector."""
        return [o.id for o in self.prep_opportunities if o.selected]

    @rx.var
    def selected_experiment_ids(self) -> list[int]:
        """IDs of experiments checked in the prep page selector."""
        return [e.id for e in self.prep_running_experiments if e.selected]

    @rx.var
    def visible_prep_experiments(self) -> list[PrepExperimentItem]:
        """Running experiments for currently selected prep opportunities."""
        sel_ids = {o.id for o in self.prep_opportunities if o.selected}
        if not sel_ids:
            return []
        return [e for e in self.prep_running_experiments if e.opp_id in sel_ids]

    def copy_guide_to_clipboard(self):
        """Copies the generated prep guide text to the system clipboard."""
        import json as _json
        return rx.call_script(
            f"navigator.clipboard.writeText({_json.dumps(self.prep_questions)})"
        )

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
    "ParticipantItem",
]
