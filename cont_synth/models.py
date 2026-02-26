import reflex as rx
from sqlmodel import Field
from datetime import datetime, timezone
from typing import Optional

class Persona(rx.Model, table=True):
    name: str = Field(unique=True, index=True)

class Interview(rx.Model, table=True):
    persona_id: int = Field(foreign_key="persona.id")
    transcript: str
    quality_score: int
    feedback: str
    memorable_quote: str
    date_logged: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Opportunity(rx.Model, table=True):
    """The Master Opportunity that spans multiple interviews/personas."""
    theme: str = Field(default="Uncategorized")
    statement: str
    parent_id: int | None = Field(default=None, foreign_key="opportunity.id") # NESTED OPPS
    date_last_validated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InterviewOpportunityLink(rx.Model, table=True):
    """The Many-to-Many bridge storing the specific quote for that specific interview."""
    interview_id: int = Field(foreign_key="interview.id", primary_key=True)
    opportunity_id: int = Field(foreign_key="opportunity.id", primary_key=True)
    source_quote: str

# --- NEW OST DATABASE MODELS ---

class Outcome(rx.Model, table=True):
    """The root of the tree: The business or product goal we are driving."""
    name: str
    description: str
    target_metric: str = "" # e.g., "Reduce churn by 5%"
    is_active: bool = True

class OutcomeOpportunityLink(rx.Model, table=True):
    """Bridge table: Maps Opportunities to Business Outcomes."""
    outcome_id: int = Field(foreign_key="outcome.id", primary_key=True)
    opportunity_id: int = Field(foreign_key="opportunity.id", primary_key=True)

class Solution(rx.Model, table=True):
    """The leaves of the tree: Competing ideas to solve a specific opportunity."""
    opportunity_id: int = Field(foreign_key="opportunity.id")
    parent_id: int | None = Field(default=None, foreign_key="solution.id") # <--- NEW: Allows sub-solutions
    name: str
    description: str
    status: str = "Ideation" # Status pipeline: Ideation -> Testing -> Discarded -> Shipped