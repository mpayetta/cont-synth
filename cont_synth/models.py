import reflex as rx
from sqlmodel import Field, SQLModel
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, LargeBinary
from pgvector.sqlalchemy import Vector


class Product(rx.Model, table=True):
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Persona(rx.Model, table=True):
    name: str = Field(unique=True, index=True)


class Interview(rx.Model, table=True):
    product_id: int | None = Field(default=1, foreign_key="product.id")
    persona_id: int = Field(foreign_key="persona.id")
    transcript: str
    quality_score: int
    feedback: str
    memorable_quote: str
    date_logged: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Metadata extracted by LLM — all optional
    duration_minutes: int | None = Field(default=None)
    interview_date: str | None = Field(default=None)   # ISO format: YYYY-MM-DD
    participants: str | None = Field(default=None)     # JSON-encoded list of names


class Opportunity(rx.Model, table=True):
    """The Master Opportunity that spans multiple interviews/personas."""

    product_id: int | None = Field(default=1, foreign_key="product.id")
    theme: str = Field(default="Uncategorized")
    statement: str
    parent_id: int | None = Field(
        default=None, foreign_key="opportunity.id"
    )  # NESTED OPPS
    date_last_validated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Teresa Torres prioritization scores (0 = unrated, 1–5)
    impact_score: int = Field(default=0)
    sat_gap_score: int = Field(default=0)


class InterviewOpportunityLink(SQLModel, table=True):
    """The Many-to-Many bridge storing the specific quote for that specific interview."""

    interview_id: int = Field(foreign_key="interview.id", primary_key=True)
    opportunity_id: int = Field(foreign_key="opportunity.id", primary_key=True)
    source_quote: str


class Outcome(rx.Model, table=True):
    """The root of the tree: The business or product goal we are driving."""

    product_id: int | None = Field(default=1, foreign_key="product.id")
    name: str
    description: str
    target_metric: str = ""  # e.g., "Reduce churn by 5%"
    is_active: bool = True


class OutcomeOpportunityLink(SQLModel, table=True):
    """Bridge table: Maps Opportunities to Business Outcomes."""

    outcome_id: int = Field(foreign_key="outcome.id", primary_key=True)
    opportunity_id: int = Field(foreign_key="opportunity.id", primary_key=True)


class Solution(rx.Model, table=True):
    """The leaves of the tree: Competing ideas to solve a specific opportunity."""

    opportunity_id: int = Field(foreign_key="opportunity.id")
    parent_id: int | None = Field(
        default=None, foreign_key="solution.id"
    )  # <--- NEW: Allows sub-solutions
    name: str
    description: str
    status: str = (
        "Ideation"  # Status pipeline: Ideation -> Testing -> Discarded -> Shipped
    )

class Experiment(rx.Model, table=True):
    """Tests designed to validate assumptions behind a solution."""

    solution_id: int = Field(foreign_key="solution.id")
    name: str
    assumption: str       # e.g., "Users are willing to pay for this."
    description: str = "" # What exactly will we do / how will we run it?
    success_metric: str = "" # How will we know it worked?
    method: str           # e.g., "Fake Door", "A/B Test", "Prototype Interview"

    # State management
    status: str = "Draft" # Draft -> Running -> Concluded
    signal: str = "Pending" # Pending -> Validated -> Invalidated

    # Telemetry & Proof
    evidence_notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Participant(rx.Model, table=True):
    """A real human the team has talked to across one or more interviews."""

    name: str = Field(index=True)
    persona_id: int | None = Field(default=None, foreign_key="persona.id")  # their role archetype
    is_team_member: bool = Field(default=False)  # True = product team interviewer, not a customer
    segment: str = Field(default="")        # e.g. "Enterprise", "SMB"
    recruited_via: str = Field(default="")  # e.g. "LinkedIn", "Customer Success"
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InterviewParticipantLink(SQLModel, table=True):
    """Many-to-many bridge: one interview can have many participants and vice versa."""

    interview_id: int = Field(foreign_key="interview.id", primary_key=True)
    participant_id: int = Field(foreign_key="participant.id", primary_key=True)


class User(rx.Model, table=True):
    """Single-user authentication table."""

    username: str = Field(unique=True, index=True)
    password_hash: str
    fullname: str
    gemini_api_key: Optional[str] = Field(default=None)


class InterviewFeedback(rx.Model, table=True):
    """1-to-1 coaching assessment linked to an Interview."""

    interview_id: int = Field(foreign_key="interview.id", unique=True, index=True)
    score: int  # 1–10
    keep_doing: str = ""  # JSON list of strings
    stop_doing: str = ""  # JSON list of strings
    start_doing: str = ""  # JSON list of strings
    trend_analysis: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LlmUsageLog(rx.Model, table=True):
    """One row per LLM API call, capturing token usage for cost tracking."""

    model_name: str               # e.g. "gemini-2.5-pro", "gemini-2.5-flash"
    operation: str                # "synthesis", "dedupe", "prep"
    interview_id: int | None = Field(default=None, foreign_key="interview.id")
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PrepGuideLog(rx.Model, table=True):
    """Historical log of every generated interview prep guide, including full input context."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    guide_type: str = Field(default="battle_plan")  # "battle_plan" | "interview_guide"
    target_persona: str = Field(default="")
    content: str
    used_coach_feedback: bool = Field(default=False)
    # Input snapshot — everything the LLM received
    input_opportunities: str = Field(default="")   # JSON list of {"theme": str, "statement": str}
    input_extra_context: str = Field(default="")
    input_coach_score: int = Field(default=0)
    input_stop_doing: str = Field(default="")      # JSON list of strings


class WorkspaceDocument(rx.Model, table=True):
    """Tracks a file uploaded to the workspace Knowledge Base."""

    product_id: int | None = Field(default=1, foreign_key="product.id")
    filename: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_data: Optional[bytes] = Field(default=None, sa_column=Column(LargeBinary))


class DocumentChunk(rx.Model, table=True):
    """A chunked slice of a WorkspaceDocument with its vector embedding."""

    document_id: int = Field(foreign_key="workspacedocument.id")
    chunk_text: str
    # 384-dimensional embedding from all-MiniLM-L6-v2
    embedding: Optional[list] = Field(
        default=None, sa_column=Column(Vector(384))
    )