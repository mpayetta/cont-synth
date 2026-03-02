from pydantic import BaseModel
from typing import Optional, List

# For Gemini Pro (Synthesis)
class OpportunityExtraction(BaseModel):
    theme: str
    opportunity_statement: str
    source_quote: str

class QualityCheck(BaseModel):
    score: int
    feedback: str

class InterviewMetadata(BaseModel):
    duration_minutes: Optional[int]
    interview_date: Optional[str]  # ISO format: YYYY-MM-DD, or null
    participant_names: Optional[List[str]]  # e.g. ["Maia Fossati", "Mauricio Payetta"]
    participant_roles: Optional[List[str]]  # parallel: "interviewee" or "interviewer"

class InterviewSnapshot(BaseModel):
    quality_check: QualityCheck
    opportunities: List[OpportunityExtraction]
    memorable_quote: str
    metadata: Optional[InterviewMetadata]

# For Gemini Flash (Deduplication)
class OpportunityMatch(BaseModel):
    new_opportunity_statement: str
    matched_existing_id: Optional[int]

class DedupeResult(BaseModel):
    matches: List[OpportunityMatch]