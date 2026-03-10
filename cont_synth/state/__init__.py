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
    PrepGuideItem,
    CoachFreqItem,
    CoachDetailItem,
    WorkspaceDocumentItem,
    WorkspaceMemberItem,
    AuditLogItem,
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
    InterviewFeedback,
    PrepGuideLog,
    Solution,
    Opportunity,
    Outcome,
    Participant,
    Persona,
    Product,
    ProductMember,
    AuditLog,
)
from .navigation import NavigationStateMixin
from .synthesis import InterviewSynthesisStateMixin, _SCROLL_TO_MARK
from .interviews import InterviewPrepStateMixin
from .ledger import LedgerStateMixin
from .participants import ParticipantStateMixin
from .knowledge_base import KnowledgeBaseStateMixin

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


class State(  # pragma: no cover
    NavigationStateMixin,
    InterviewSynthesisStateMixin,
    InterviewPrepStateMixin,
    LedgerStateMixin,
    ParticipantStateMixin,
    KnowledgeBaseStateMixin,
    rx.State,
):
    """Main application state composed from feature-specific mixins."""

    # --- Authentication ---
    is_authenticated: bool = False
    auth_user_id: int = 0
    auth_username: str = ""
    auth_fullname: str = ""
    auth_user_role: str = ""
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

    # --- Performance cache flags (backend-only, not synced to frontend) ---
    _products_loaded: bool = False
    _ledger_cache_valid: bool = False
    _ledger_cache_product: str = ""

    # --- Combo-box selection key: increment to force input remount after selection ---
    combo_refresh_key: int = 0

    # --- Workspace membership ---
    workspace_role: str = ""   # "admin" | "member" | "viewer" — scoped to active product
    workspace_members: list[WorkspaceMemberItem] = []
    invite_username: str = ""
    invite_role: str = "member"
    invite_error: str = ""
    create_user_username: str = ""
    create_user_fullname: str = ""
    create_user_password: str = ""
    create_user_workspace_role: str = "member"
    create_user_error: str = ""

    # --- Audit log ---
    audit_logs: list[AuditLogItem] = []
    audit_log_page: int = 0
    audit_log_total: int = 0
    audit_filter_action: str = ""
    audit_filter_entity_type: str = ""

    # --- Interview & prep state ---
    is_processing: bool = False
    synthesis_status: str = ""
    synthesis_phase: str = ""
    synthesis_ready: bool = False
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
    apply_coach_feedback: bool = True
    last_interview_score: int = 0
    last_stop_doing: list[str] = []
    guide_history: list[PrepGuideItem] = []
    selected_guide_id: int = -1
    guide_drawer_open: bool = False

    interview_history: list[InterviewHistoryItem] = []

    # --- Interview log filters + pagination ---
    interviews_log_page: int = 0
    interviews_log_total: int = 0
    interviews_log_date_from: str = ""
    interviews_log_date_to: str = ""
    interviews_log_filter_participants: list[str] = []
    available_log_participants: list[str] = []

    # --- Ledger & personas ---
    ledger_data: list[LedgerItem] = []
    available_personas: list[str] = []
    target_persona: str = ""
    ledger_view_mode: str = "list"  # "table" | "list" | "board" | "matrix"
    collapsed_themes: list[str] = []

    # --- Opportunity list filters ---
    opp_filter_themes: list[str] = []
    opp_filter_personas: list[str] = []
    opp_filter_priority: str = ""   # "" | "high" | "medium" | "low" | "unrated"
    opp_filter_search: str = ""

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
    manual_opp_outcome_name: str = "None"
    is_opp_dialog_open: bool = False
    is_editing_opp_detail: bool = False
    is_delete_confirm_open: bool = False
    pending_delete_opp_id: int = -1
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
    interview_detail_quality: int = 0
    # Coach feedback (loaded from DB on interview detail page)
    interview_detail_coach_score: int = 0
    interview_detail_coach_keep: list[CoachDetailItem] = []
    interview_detail_coach_stop: list[CoachDetailItem] = []
    interview_detail_coach_start: list[CoachDetailItem] = []
    interview_detail_coach_trend: str = ""
    is_generating_coach: bool = False

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

    # --- Pending coach feedback (held until confirm_synthesis writes to DB) ---
    pending_coach_score: int = 0
    pending_coach_keep: list[str] = []
    pending_coach_stop: list[str] = []
    pending_coach_start: list[str] = []
    pending_coach_trend: str = ""

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

    # --- Combobox UI ---
    open_combo: str = ""

    # --- Participant CRM ---
    participants: list[ParticipantItem] = []
    participant_segments: list[str] = []
    participant_recruited_vias: list[str] = []
    show_team_members: bool = False

    # --- Participant filters ---
    participants_filter_name: str = ""
    participants_filter_personas: list[str] = []
    participants_filter_segments: list[str] = []
    participants_filter_date_from: str = ""
    participants_filter_date_to: str = ""
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

    # --- Coach dashboard ---
    coach_score_history: list[dict] = []
    coach_top_stop_doing: list[CoachFreqItem] = []
    coach_top_keep_doing: list[CoachFreqItem] = []

    # --- Knowledge Base ---
    kb_documents: list[WorkspaceDocumentItem] = []
    kb_is_uploading: bool = False
    kb_is_reprocessing: bool = False
    kb_upload_error: str = ""

    @rx.var
    def is_admin(self) -> bool:
        return self.auth_user_role == "admin"

    @rx.var
    def kb_document_count(self) -> int:
        return len(self.kb_documents)

    @rx.var
    def outcome_choices_for_dialog(self) -> list[str]:
        return ["None"] + [o.name for o in self.outcomes]

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
        self.auth_user_role = user.role
        self.is_authenticated = True
        self.login_error = ""
        self.login_username = ""
        self.login_password = ""
        self._products_loaded = False
        self._ledger_cache_valid = False
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
        self.auth_user_role = ""
        self._products_loaded = False
        self._ledger_cache_valid = False
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
        self.auth_user_role = user.role
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
    def set_apply_coach_feedback(self, val: bool): self.apply_coach_feedback = val
    def set_selected_guide_id(self, guide_id: int): self.selected_guide_id = guide_id

    def open_guide_drawer(self, guide_id: int):
        self.selected_guide_id = guide_id
        self.guide_drawer_open = True

    def close_guide_drawer(self):
        self.guide_drawer_open = False
    def set_ledger_view_mode(self, val: str): self.ledger_view_mode = val
    def toggle_opp_filter_theme(self, name: str):
        if name in self.opp_filter_themes:
            self.opp_filter_themes = [t for t in self.opp_filter_themes if t != name]
        else:
            self.opp_filter_themes = self.opp_filter_themes + [name]
    def toggle_opp_filter_persona(self, name: str):
        if name in self.opp_filter_personas:
            self.opp_filter_personas = [p for p in self.opp_filter_personas if p != name]
        else:
            self.opp_filter_personas = self.opp_filter_personas + [name]
    def set_opp_filter_priority(self, val: str): self.opp_filter_priority = "" if val == "__all__" else val
    def set_opp_filter_search(self, val: str): self.opp_filter_search = val
    def clear_opp_filters(self):
        self.opp_filter_themes = []
        self.opp_filter_personas = []
        self.opp_filter_priority = ""
        self.opp_filter_search = ""
    def set_new_solution_name(self, val: str): self.new_solution_name = val
    def set_new_solution_desc(self, val: str): self.new_solution_desc = val
    def set_new_solution_status(self, val: str): self.new_solution_status = val
    def set_new_outcome_name(self, val: str): self.new_outcome_name = val
    def set_manual_opp_theme(self, val: str): self.manual_opp_theme = val
    def set_manual_opp_statement(self, val: str): self.manual_opp_statement = val
    def set_manual_opp_parent_id(self, val: str): self.manual_opp_parent_id = val
    def set_manual_opp_outcome_name(self, val: str): self.manual_opp_outcome_name = val
    def set_selected_interview_choice(self, val: str): self.selected_interview_choice = val
    def set_participants_filter_name(self, val: str): self.participants_filter_name = val
    def toggle_participants_filter_persona(self, name: str):
        if name in self.participants_filter_personas:
            self.participants_filter_personas = [p for p in self.participants_filter_personas if p != name]
        else:
            self.participants_filter_personas = self.participants_filter_personas + [name]
    def toggle_participants_filter_segment(self, name: str):
        if name in self.participants_filter_segments:
            self.participants_filter_segments = [s for s in self.participants_filter_segments if s != name]
        else:
            self.participants_filter_segments = self.participants_filter_segments + [name]
    def set_participants_filter_date_from(self, val: str): self.participants_filter_date_from = val
    def set_participants_filter_date_to(self, val: str): self.participants_filter_date_to = val
    def clear_participants_filters(self):
        self.participants_filter_name = ""
        self.participants_filter_personas = []
        self.participants_filter_segments = []
        self.participants_filter_date_from = ""
        self.participants_filter_date_to = ""
        self.show_team_members = False
    def set_participant_form_name(self, val: str): self.participant_form_name = val
    def set_participant_form_persona(self, val: str): self.participant_form_persona = val
    def set_participant_form_is_team_member(self, val: bool): self.participant_form_is_team_member = val
    def set_participant_form_segment(self, val: str): self.participant_form_segment = val
    def set_participant_form_recruited_via(self, val: str): self.participant_form_recruited_via = val
    def set_participant_form_notes(self, val: str): self.participant_form_notes = val

    def open_combo_box(self, field_id: str): self.open_combo = field_id
    def close_combo_box(self): self.open_combo = ""
    def select_combo_option(self, field_id: str, value: str):
        self.open_combo = ""
        self.combo_refresh_key += 1  # force combo inputs to remount with the new default_value
        if field_id == "synthesize_persona":
            self.persona_input = value
        elif field_id == "participant_persona":
            self.participant_form_persona = value
        elif field_id == "participant_segment":
            self.participant_form_segment = value
        elif field_id == "participant_recruited_via":
            self.participant_form_recruited_via = value
        elif field_id == "opp_theme":
            self.manual_opp_theme = value
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

    async def scroll_to_timestamp(self, ts: str):
        """Highlight the timestamp in the transcript and scroll to it."""
        self.highlighted_quote_text = ts
        self.scroll_trigger += 1
        yield
        yield rx.call_script(_SCROLL_TO_MARK)

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
        """Delete all data in the active workspace. Workspace admins only."""
        if not self.is_workspace_admin:
            return
        prod_id = int(self.active_product_id)
        with rx.session() as session:
            inv_ids = [
                i.id for i in session.exec(
                    select(Interview).where(Interview.product_id == prod_id)
                ).all()
            ]
            opp_ids = [
                o.id for o in session.exec(
                    select(Opportunity).where(Opportunity.product_id == prod_id)
                ).all()
            ]
            sol_ids = (
                [s.id for s in session.exec(
                    select(Solution).where(Solution.opportunity_id.in_(opp_ids))
                ).all()]
                if opp_ids else []
            )

            # Delete in FK-safe order (children before parents)
            if sol_ids:
                for row in session.exec(select(Experiment).where(Experiment.solution_id.in_(sol_ids))).all():
                    session.delete(row)
            if inv_ids:
                for row in session.exec(select(InterviewParticipantLink).where(InterviewParticipantLink.interview_id.in_(inv_ids))).all():
                    session.delete(row)
                for row in session.exec(select(InterviewOpportunityLink).where(InterviewOpportunityLink.interview_id.in_(inv_ids))).all():
                    session.delete(row)
                for row in session.exec(select(LlmUsageLog).where(LlmUsageLog.interview_id.in_(inv_ids))).all():
                    session.delete(row)
                for row in session.exec(select(InterviewFeedback).where(InterviewFeedback.interview_id.in_(inv_ids))).all():
                    session.delete(row)
            if opp_ids:
                for row in session.exec(select(OutcomeOpportunityLink).where(OutcomeOpportunityLink.opportunity_id.in_(opp_ids))).all():
                    session.delete(row)
                for row in session.exec(select(Solution).where(Solution.opportunity_id.in_(opp_ids), Solution.parent_id != None)).all():
                    session.delete(row)
                for row in session.exec(select(Solution).where(Solution.opportunity_id.in_(opp_ids))).all():
                    session.delete(row)
                for row in session.exec(select(Opportunity).where(Opportunity.product_id == prod_id, Opportunity.parent_id != None)).all():
                    session.delete(row)
                for row in session.exec(select(Opportunity).where(Opportunity.product_id == prod_id)).all():
                    session.delete(row)
            for row in session.exec(select(Outcome).where(Outcome.product_id == prod_id)).all():
                session.delete(row)
            for row in session.exec(select(Interview).where(Interview.product_id == prod_id)).all():
                session.delete(row)
            # Scoped participants
            for row in session.exec(select(Participant).where(Participant.product_id == prod_id)).all():
                session.delete(row)
            session.commit()

        # Reset volatile state for this workspace
        self.interview_history = []
        self.ledger_data = []
        self.participants = []
        self.outcomes = []
        self.outcome_names = ["All Outcomes"]
        self.active_outcome_name = "All Outcomes"
        self.pending_synthesis_opps = []
        self.pending_synthesis_participants = []
        self.pending_synthesis_participant_roles = []
        self.prep_opportunities = []
        self.prep_running_experiments = []
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
        result = self._ensure_auth_and_load()
        if self.is_viewer:
            return rx.redirect("/opportunities")
        return result

    def load_review_page(self):
        self.current_view = "synthesis_review"
        self.synthesis_ready = False
        return self._ensure_auth_and_load()

    def go_to_review(self):
        self.synthesis_ready = False
        return rx.redirect("/review")

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
        result = self._ensure_auth_and_load()
        if self.is_viewer:
            return rx.redirect("/opportunities")
        return result

    def load_participants_page(self):
        self.current_view = "participants"
        return self._ensure_auth_and_load()

    def load_llm_usage_page(self):
        self.current_view = "llm_usage"
        return self._ensure_auth_and_load()

    def load_knowledge_base_page(self):
        self.current_view = "knowledge_base"
        return self._ensure_auth_and_load()

    def load_members_page(self):
        self.current_view = "members"
        return self._ensure_auth_and_load()

    def load_about_page(self):
        self.current_view = "about"
        return self._ensure_auth_and_load()

    def set_audit_filter_action(self, value: str):
        self.audit_filter_action = value
        self.audit_log_page = 0
        self.load_audit_logs()

    def set_audit_filter_entity_type(self, value: str):
        self.audit_filter_entity_type = value
        self.audit_log_page = 0
        self.load_audit_logs()

    def clear_audit_filters(self):
        self.audit_filter_action = ""
        self.audit_filter_entity_type = ""
        self.audit_log_page = 0
        self.load_audit_logs()

    def audit_log_next_page(self):
        self.audit_log_page += 1
        self.load_audit_logs()

    def audit_log_prev_page(self):
        if self.audit_log_page > 0:
            self.audit_log_page -= 1
        self.load_audit_logs()

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
    def participants_filters_active(self) -> bool:
        return bool(
            self.participants_filter_name
            or self.participants_filter_personas
            or self.participants_filter_segments
            or self.participants_filter_date_from
            or self.participants_filter_date_to
            or self.show_team_members
        )

    @rx.var
    def filtered_participants(self) -> list[ParticipantItem]:
        """Participants list with all active filters applied."""
        items = self.participants
        # Team member visibility
        if not self.show_team_members:
            items = [p for p in items if not p.is_team_member]
        # Name search
        if self.participants_filter_name:
            q = self.participants_filter_name.lower()
            items = [p for p in items if q in p.name.lower()]
        # Persona multi-select
        if self.participants_filter_personas:
            items = [p for p in items if p.persona_name in self.participants_filter_personas]
        # Segment multi-select
        if self.participants_filter_segments:
            items = [p for p in items if p.segment in self.participants_filter_segments]
        # Date from (last_interviewed >= date_from)
        if self.participants_filter_date_from:
            items = [p for p in items if p.last_interviewed >= self.participants_filter_date_from]
        # Date to (last_interviewed <= date_to)
        if self.participants_filter_date_to:
            items = [p for p in items if p.last_interviewed and p.last_interviewed <= self.participants_filter_date_to]
        return items

    @rx.var
    def available_themes(self) -> list[str]:
        seen = []
        for item in self.ledger_data:
            if item.theme and item.theme not in seen:
                seen.append(item.theme)
        return sorted(seen)

    @rx.var
    def filtered_opp_themes(self) -> list[str]:
        q = self.manual_opp_theme.lower()
        if not q or q == "uncategorized":
            return self.available_themes
        return [t for t in self.available_themes if q in t.lower()]

    @rx.var
    def filtered_synthesize_personas(self) -> list[str]:
        q = self.persona_input.lower()
        if not q:
            return self.available_personas
        return [p for p in self.available_personas if q in p.lower()]

    @rx.var
    def filtered_participant_personas(self) -> list[str]:
        q = self.participant_form_persona.lower()
        if not q:
            return self.available_personas
        return [p for p in self.available_personas if q in p.lower()]

    @rx.var
    def filtered_participant_segments(self) -> list[str]:
        q = self.participant_form_segment.lower()
        if not q:
            return self.participant_segments
        return [p for p in self.participant_segments if q in p.lower()]

    @rx.var
    def filtered_participant_recruited_vias(self) -> list[str]:
        q = self.participant_form_recruited_via.lower()
        if not q:
            return self.participant_recruited_vias
        return [p for p in self.participant_recruited_vias if q in p.lower()]

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

    @rx.var
    def selected_guide_item(self) -> PrepGuideItem:
        """The currently selected guide entry for the history side panel."""
        for g in self.guide_history:
            if g.id == self.selected_guide_id:
                return g
        return PrepGuideItem(id=-1, created_at="", guide_type="", target_persona="", content="", used_coach_feedback=False)

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
