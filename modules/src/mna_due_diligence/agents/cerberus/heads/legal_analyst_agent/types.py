import operator
from typing import TypedDict, Annotated, List, Union, Literal
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from typing import Literal, List, Optional
from pydantic import BaseModel, Field



class RiskFinding(BaseModel):
    """A specific risk identified in a contract."""
    filename: str = Field(..., description="The name of the file where the risk was found.")
    risk_category: str = Field(..., description="The CUAD category, e.g., 'Unlimited Liability', 'Change of Control'.")
    severity: Literal["Low", "Medium", "High", "Critical"] = Field(..., description="Subjective assessment of impact.")
    evidence_quote: str = Field(..., description="Verbatim quote from the text proving the risk.")
    reasoning: str = Field(..., description="Legal analysis of WHY this is a risk.")
    

class DataRequirement(BaseModel):
    """A request for additional data needed for analysis."""
    description: str = Field(..., description="A clear description of the additional data needed.")
    purpose: str = Field(..., description="Why this data is necessary for the analysis.")
    plan_after_data: str = Field(..., description="What the next steps will be once this data is obtained.")
    
        
class AnalystState(TypedDict):
    # Standard conversation history
    messages: Annotated[List[BaseMessage], operator.add]
    # Input Data KV pairs
    input_data: dict[str, str]
    # Expand specific data keys
    expand_given_data_keys: List[str]
    # Control loop counter
    loop_step: int
    # New risks discovered (accumulated)
    new_risks: Annotated[List[RiskFinding], operator.add]
    # Any additional data requirements
    data_requirements: Annotated[List[DataRequirement], operator.add]
    # Next step for router (tool_call, conclude, etc.)
    next_step: str
    # final output
    final_output: Optional[dict]



class AnalystOutput(BaseModel):
    """The aggregate output of the Legal Analyst's session."""
    findings: List[RiskFinding] = Field(default_factory=list)
    analysis_summary: str = Field(..., description="A brief summary of what was analyzed.")


class ReasonerOutput(BaseModel):
    """Structured output from the reasoner node."""
    new_risks: List[RiskFinding] = Field(
        default_factory=list,
        description="Any new risks discovered in this reasoning step."
    )
    summary: str = Field(
        ...,
        description="Short summary of what was done and what's next (if any)."
    )
    next_step: Literal["expand_given_data", "tool_call", "conclude", "continue_analysis"] = Field(
        ...,
        description="The next action: tool_call if tool needed, conclude if done, continue_analysis to keep reasoning."
    )
    expand_given_data_keys: List[str] = Field(..., description="List of keys from input_data to further expand.")
    data_requirements: List[DataRequirement] = Field(
        default_factory=list,
        description="Formatted request for any additional data requirements, if needed."
    )