from pydantic import BaseModel, Field
from typing import List

class Opportunity(BaseModel):
    opportunity_statement: str = Field(
        description="The underlying user need, pain point, or desire. MUST be framed as a problem, NOT a feature request or solution."
    )
    source_quote: str = Field(
        description="The exact quote from the transcript that validates this opportunity."
    )

class QualityCheck(BaseModel):
    score: int = Field(
        description="Score from 1 to 10 evaluating how well the interviewer collected specific stories about past behavior. Deduct points for hypothetical or 'typically' questions."
    )
    feedback: str = Field(
        description="Punchy, aggressive feedback on the interviewer's technique. What did they miss? Where did they lead the witness?"
    )
    flagged_questions: List[str] = Field(
        description="List of speculative, hypothetical, or 'happy path' questions the interviewer asked that violate the story-based interview framework."
    )

class InterviewSnapshot(BaseModel):
    quality_check: QualityCheck
    quick_facts: List[str] = Field(
        description="3 to 5 brief bullet points establishing the context and background of the user."
    )
    memorable_quote: str = Field(
        description="A single verbatim quote that captures the absolute essence of the user's main friction or story."
    )
    experience_map_steps: List[str] = Field(
        description="Chronological steps the user took in their specific story (e.g., '1. Logged in, 2. Searched for X, 3. Failed to find Y')."
    )
    opportunities: List[Opportunity] = Field(
        description="List of extracted opportunities derived strictly from the transcript."
    )