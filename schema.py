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

class InterviewSnapshot(BaseModel):
    quality_check: QualityCheck
    opportunities: List[OpportunityExtraction]
    memorable_quote: str

# For Gemini Flash (Deduplication)
class OpportunityMatch(BaseModel):
    new_opportunity_statement: str
    matched_existing_id: Optional[int]

class DedupeResult(BaseModel):
    matches: List[OpportunityMatch]