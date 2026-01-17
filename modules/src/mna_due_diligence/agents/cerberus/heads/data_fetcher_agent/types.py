from pydantic import BaseModel, Field
from typing import Dict


import operator
from typing import TypedDict, Annotated, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# --- STATE DEFINITION ---
class FetcherState(TypedDict):
    # Inputs
    instruction: str
    
    # Internal State
    iteration_count: int
    fetched_data: Dict[str, Any]  # The Key-Value Store (e.g., {"NDA_1_text": "..."})
    tool_logs: Annotated[List[str], operator.add] # Stats for the supervisor
    
    # Inter-node Communication
    pending_tool_calls: List[dict] # What the strategist wants to run next
    final_summary: str # The final 1-line summary


# --- STRATEGIST OUTPUT SCHEMA ---
class ToolCallArgument(BaseModel):
    name: str = Field(..., description="Name of the argument")
    value: str = Field(..., description="Value of the argument")
    
class ToolCall(BaseModel):
    tool_name: str = Field(..., description="One of: filter_contracts, filter_contracts_advanced, search_clause, read_file")
    arguments: List[ToolCallArgument] = Field(..., description="Arguments to pass to the tool.")
    output_key: str = Field(..., description="The key to save this result under (e.g., 'google_msa_text').")

class FetchStrategy(BaseModel):
    """The plan for the next hop."""
    reasoning: str = Field(..., description="Why are we running these tools?")
    tool_calls: List[ToolCall] = Field(..., description="List of tools to run. Empty if done.")
    is_complete: bool = Field(..., description="True if we have all data or cannot find it.")