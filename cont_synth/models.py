import reflex as rx
from sqlmodel import Field
from datetime import datetime, timezone
from typing import Optional


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


class InterviewOpportunityLink(rx.Model, table=True):
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


class OutcomeOpportunityLink(rx.Model, table=True):
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
    assumption: str # e.g., "Users are willing to pay for this."
    method: str # e.g., "Fake Door", "A/B Test", "Prototype Interview"
    
    # State management
    status: str = "Draft" # Draft -> Running -> Concluded
    signal: str = "Pending" # Pending -> Validated -> Invalidated
    
    # Telemetry & Proof
    evidence_notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))