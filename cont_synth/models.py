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
    date_last_validated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class InterviewOpportunityLink(rx.Model, table=True):
    """The Many-to-Many bridge storing the specific quote for that specific interview."""
    interview_id: int = Field(foreign_key="interview.id", primary_key=True)
    opportunity_id: int = Field(foreign_key="opportunity.id", primary_key=True)
    source_quote: str