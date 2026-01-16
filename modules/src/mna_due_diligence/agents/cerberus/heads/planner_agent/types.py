from typing import List, Literal
from pydantic import BaseModel, Field

class Step(BaseModel):
    id: int = Field(..., description="Unique step ID (1, 2, 3...)")
    agent: Literal["data_fetcher", "legal_analyst", "report_writer"] = Field(..., description="Which agent handles this step?")
    instruction: str = Field(..., description="Specific, executable instruction for that agent.")
    dependency: int = Field(0, description="ID of the step that must complete before this one (0 if none).")

class AuditPlan(BaseModel):
    """The strategic plan for the M&A Audit."""
    reasoning: str = Field(..., description="Brief explanation of why this plan was chosen.")
    steps: List[Step]