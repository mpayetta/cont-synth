import os
from datetime import datetime

import google.generativeai as genai
import reflex as rx
from sqlmodel import Field
from dotenv import load_dotenv


# --- AI & Prompt Infrastructure ---
load_dotenv()

_env_gemini_key = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=_env_gemini_key)

pro_model = genai.GenerativeModel("gemini-2.5-pro")
flash_model = genai.GenerativeModel("gemini-2.5-flash")


def configure_genai(api_key: str) -> None:
    """Reconfigure the Gemini client with a new API key.

    Falls back to the GEMINI_API_KEY env var when api_key is empty.
    Also refreshes the module-level model references so all subsequent
    LLM calls pick up the new key.
    """
    global pro_model, flash_model
    effective_key = api_key.strip() if api_key.strip() else _env_gemini_key
    genai.configure(api_key=effective_key)
    pro_model = genai.GenerativeModel("gemini-2.5-pro")
    flash_model = genai.GenerativeModel("gemini-2.5-flash")


def load_prompt(filename: str) -> str:
    """Reads prompt templates from the prompts directory."""
    filepath = os.path.join(os.getcwd(), "prompts", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# --- UI DATA MODELS ---
class ProductItem(rx.Base):
    id: int
    name: str


class PersonaBadge(rx.Base):
    name: str
    color: str


class QuoteItem(rx.Base):
    interview_id: int
    persona_name: str
    persona_color: str
    text: str
    opportunity_statement: str = ""


class SolutionItem(rx.Base):
    id: int
    parent_id: int | None = None
    name: str
    description: str
    status: str
    indent_level: int = 0
    
class ExperimentItem(rx.Base):
    id: int
    solution_id: int
    solution_name: str  # carry this for display in the tab
    name: str
    assumption: str
    method: str         # "Fake Door", "A/B Test", "Prototype Interview"
    status: str         # "Draft", "Running", "Concluded"
    signal: str         # "Pending", "Validated", "Invalidated"
    evidence_notes: str


class PendingLlmUsage(rx.Base):
    """Token usage from one LLM call, held in state until the Interview row exists."""

    model_name: str
    operation: str
    prompt_tokens: int
    output_tokens: int
    total_tokens: int


class LlmUsageItem(rx.Base):
    """One row in the LLM Usage dashboard."""

    id: int
    model_name: str
    operation: str
    interview_id: int
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    created_at: str


class PendingOppItem(rx.Base):
    """One AI-extracted opportunity awaiting user confirmation before DB write."""
    index: int
    opportunity_statement: str
    theme: str
    source_quote: str
    matched_existing_id: int = -1       # -1 = new opp; positive int = existing opp ID
    matched_existing_statement: str = ""
    selected: bool = True


class OppDetailSolution(rx.Base):
    """A solution with its experiments embedded, used in the full-page detail view."""
    id: int
    parent_id: int | None = None
    name: str
    description: str
    status: str
    indent_level: int = 0
    experiments: list[ExperimentItem] = []


class OutcomeItem(rx.Base):
    id: int
    name: str


class InterviewHistoryItem(rx.Base):
    interview_id: int
    persona: str
    persona_color: str = "gray"
    date_logged: str
    snippet: str
    # Extracted metadata (empty/0 = not available)
    interview_date: str = ""
    duration_minutes: int = 0
    participants: str = ""  # comma-joined display string


class LedgerItem(rx.Base):
    opportunity_id: int
    parent_id: int = -1
    indent_level: int = 0
    theme: str
    personas_affected: list[PersonaBadge]
    opportunity: str
    status: str
    status_color: str
    days_old: int
    is_cross_functional: bool
    evidence: list[QuoteItem]
    solutions: list[SolutionItem] = []
    linked_outcomes: list[OutcomeItem] = []
    experiments: list[ExperimentItem] = []
    # Teresa Torres prioritization (0 = unrated, 1–5)
    impact_score: int = 0
    sat_gap_score: int = 0
    # priority_score = impact + sat_gap + min(evidence_count, 5), max 15
    priority_score: int = 0
    running_experiments: int = 0
    is_target: bool = False


class ParticipantItem(rx.Base):
    id: int
    name: str
    persona_name: str = ""      # role archetype, e.g. "VP of Engineering"
    persona_color: str = "gray"
    is_team_member: bool = False  # True = product team interviewer, not a customer
    segment: str
    recruited_via: str
    notes: str
    interview_count: int = 0    # computed at load, not stored
    last_interviewed: str = ""  # ISO date of most recent linked interview


class PendingParticipantItem(rx.Base):
    """One participant extracted from a pending synthesis, with an editable role."""
    index: int
    name: str
    role: str = "interviewee"  # "interviewee" or "interviewer"


class DetailParticipantItem(rx.Base):
    """One participant shown read-only in the interview detail view."""
    name: str
    is_team_member: bool = False


class DashboardBarItem(rx.Base):
    """One column in the home dashboard weekly bar chart."""
    week_label: str   # e.g. "Jan 20"
    count: int
    height_css: str = "0px"  # pre-computed CSS height for the bar, e.g. "32px"


class RecentInterviewItem(rx.Base):
    """One row in the home dashboard recent activity feed."""
    interview_id: int
    persona: str
    persona_color: str
    date_str: str
    quote_count: int


class PrepOppItem(rx.Base):
    """One opportunity shown in the prep page OST selector."""
    id: int
    theme: str
    statement: str
    selected: bool = False


class PrepExperimentItem(rx.Base):
    """One running experiment shown in the prep page assumption selector."""
    id: int
    opp_id: int
    solution_name: str
    experiment_name: str
    assumption: str
    selected: bool = False


class PersonaPrep(rx.Model, table=True):
    """Stores the latest generated prep script for a specific persona."""

    persona: str = Field(primary_key=True)
    content: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "genai",
    "pro_model",
    "flash_model",
    "configure_genai",
    "load_prompt",
    "PersonaBadge",
    "QuoteItem",
    "SolutionItem",
    "ExperimentItem",
    "OppDetailSolution",
    "OutcomeItem",
    "InterviewHistoryItem",
    "LedgerItem",
    "PersonaPrep",
    "ProductItem",
    "PendingOppItem",
    "LlmUsageItem",
    "ParticipantItem",
    "DashboardBarItem",
    "RecentInterviewItem",
    "PrepOppItem",
    "PrepExperimentItem",
]
