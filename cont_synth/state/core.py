import os
from datetime import datetime

import google.generativeai as genai
import reflex as rx
from sqlmodel import Field
from dotenv import load_dotenv


# --- AI & Prompt Infrastructure ---
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

pro_model = genai.GenerativeModel("gemini-2.5-pro")
flash_model = genai.GenerativeModel("gemini-2.5-flash")


def load_prompt(filename: str) -> str:
    """Reads prompt templates from the prompts directory."""
    filepath = os.path.join(os.getcwd(), "prompts", filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# --- UI DATA MODELS ---
class PersonaBadge(rx.Base):
    name: str
    color: str


class QuoteItem(rx.Base):
    interview_id: int
    persona_name: str
    persona_color: str
    text: str


class SolutionItem(rx.Base):
    id: int
    parent_id: int | None = None
    name: str
    description: str
    status: str
    indent_level: int = 0


class OutcomeItem(rx.Base):
    id: int
    name: str


class InterviewHistoryItem(rx.Base):
    interview_id: int
    persona: str
    date_logged: str
    snippet: str


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


class PersonaPrep(rx.Model, table=True):
    """Stores the latest generated prep script for a specific persona."""

    persona: str = Field(primary_key=True)
    content: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "genai",
    "pro_model",
    "flash_model",
    "load_prompt",
    "PersonaBadge",
    "QuoteItem",
    "SolutionItem",
    "OutcomeItem",
    "InterviewHistoryItem",
    "LedgerItem",
    "PersonaPrep",
]

