import os
from datetime import datetime

import google.generativeai as genai
import reflex as rx
from pydantic import BaseModel
from sqlmodel import Field, SQLModel
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
class ProductItem(BaseModel):
    id: int
    name: str


class PersonaBadge(BaseModel):
    name: str
    color: str


class QuoteItem(BaseModel):
    interview_id: int
    persona_name: str
    persona_color: str
    text: str
    opportunity_statement: str = ""


class SolutionItem(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    description: str
    status: str
    indent_level: int = 0
    
class ExperimentItem(BaseModel):
    id: int
    solution_id: int
    solution_name: str  # carry this for display in the tab
    name: str
    assumption: str
    description: str
    success_metric: str
    method: str         # "Fake Door", "A/B Test", "Prototype Interview"
    status: str         # "Draft", "Running", "Concluded"
    signal: str         # "Pending", "Validated", "Invalidated"
    evidence_notes: str


class PendingLlmUsage(BaseModel):
    """Token usage from one LLM call, held in state until the Interview row exists."""

    model_name: str
    operation: str
    prompt_tokens: int
    output_tokens: int
    total_tokens: int


class LlmUsageItem(BaseModel):
    """One row in the LLM Usage dashboard."""

    id: int
    model_name: str
    operation: str
    interview_id: int
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    created_at: str


class PendingOppItem(BaseModel):
    """One AI-extracted opportunity awaiting user confirmation before DB write."""
    index: int
    opportunity_statement: str
    theme: str
    source_quote: str
    matched_existing_id: int = -1       # -1 = new opp; positive int = existing opp ID
    matched_existing_statement: str = ""
    selected: bool = True


class OppDetailSolution(BaseModel):
    """A solution with its experiments embedded, used in the full-page detail view."""
    id: int
    parent_id: int | None = None
    name: str
    description: str
    status: str
    indent_level: int = 0
    experiments: list[ExperimentItem] = []


class OutcomeItem(BaseModel):
    id: int
    name: str


class InterviewHistoryItem(BaseModel):
    interview_id: int
    persona: str
    persona_color: str = "gray"
    date_logged: str
    snippet: str
    # Extracted metadata (empty/0 = not available)
    interview_date: str = ""
    duration_minutes: int = 0
    participants: str = ""  # comma-joined display string


class LedgerItem(BaseModel):
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


class ThemeGroup(BaseModel):
    """A group of opportunities sharing the same theme, for the grouped list view."""
    theme: str
    count: int
    avg_priority: int
    collapsed: bool = False
    opps: list[LedgerItem] = []


class BoardColumn(BaseModel):
    """One column in the Kanban board view, representing a priority tier."""
    label: str
    color: str
    opps: list[LedgerItem] = []


class MatrixCell(BaseModel):
    """One cell in the 5×5 Impact × Sat-Gap priority matrix."""
    sat_gap: int
    impact: int
    opps: list[LedgerItem] = []
    is_sweet_spot: bool = False  # sat_gap ≥ 3 and impact ≥ 3


class ParticipantItem(BaseModel):
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


class PendingParticipantItem(BaseModel):
    """One participant extracted from a pending synthesis, with an editable role."""
    index: int
    name: str
    role: str = "interviewee"  # "interviewee" or "interviewer"


class DetailParticipantItem(BaseModel):
    """One participant shown read-only in the interview detail view."""
    name: str
    is_team_member: bool = False


class DashboardBarItem(BaseModel):
    """One column in the home dashboard weekly bar chart."""
    week_label: str   # e.g. "Jan 20"
    count: int
    height_css: str = "0px"  # pre-computed CSS height for the bar, e.g. "32px"


class RecentInterviewItem(BaseModel):
    """One row in the home dashboard recent activity feed."""
    interview_id: int
    persona: str
    persona_color: str
    date_str: str
    quote_count: int


class PrepOppItem(BaseModel):
    """One opportunity shown in the prep page OST selector."""
    id: int
    theme: str
    statement: str
    selected: bool = False


class PrepExperimentItem(BaseModel):
    """One running experiment shown in the prep page assumption selector."""
    id: int
    opp_id: int
    solution_name: str
    experiment_name: str
    assumption: str
    selected: bool = False


class PrepGuideItem(BaseModel):
    """One saved guide entry shown in the Guide History tab."""
    id: int
    created_at: str
    guide_type: str
    target_persona: str
    content: str
    used_coach_feedback: bool
    # Saved input snapshot
    input_opportunities: list[dict] = []   # [{"theme": str, "statement": str}]
    input_extra_context: str = ""
    input_coach_score: int = 0
    input_stop_doing: list[str] = []


class CoachScorePoint(BaseModel):
    """One data point in the coach score trend chart."""
    date: str           # x-axis label, e.g. "2026-02-15"
    score: int          # y-axis value, 1–10
    interview_id: int


class CoachFreqItem(BaseModel):
    """An aggregated coaching item with its frequency across interviews."""
    text: str
    count: int


class CoachDetailItem(BaseModel):
    """A single coach feedback item with clean text and extracted timestamps."""
    text: str
    first_timestamp: str = ""       # used as scroll target on click
    all_timestamps_str: str = ""    # display string, e.g. "0:47, 6:43"


class PersonaPrep(SQLModel, table=True):
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
    "ThemeGroup",
    "BoardColumn",
    "MatrixCell",
    "PersonaPrep",
    "ProductItem",
    "PendingOppItem",
    "LlmUsageItem",
    "ParticipantItem",
    "DashboardBarItem",
    "RecentInterviewItem",
    "PrepOppItem",
    "PrepExperimentItem",
    "CoachScorePoint",
    "CoachFreqItem",
]
