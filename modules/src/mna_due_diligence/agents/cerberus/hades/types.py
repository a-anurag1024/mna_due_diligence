import operator
from typing import TypedDict, Annotated, List, Union, Dict, Any, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


# --- TIER 1: RECEPTIONIST STATE (Persistent) ---
class ReceptionistState(TypedDict):
    """
    The permanent memory of the chatbot session.
    """
    messages: Annotated[List[BaseMessage], operator.add] # Chat History
    risk_register: Annotated[List[dict], operator.add]   # Global List of Risks Found
    user_id: str



# --- TIER 2: ORCHESTRATOR (Hades) STATE (Ephemeral) ---
class HadesState(TypedDict):
    """
    The scratchpad for a single complex audit mission.
    """
    # Input
    mission: str
    
    # Internal Workflow Data
    plan: List[dict]
    current_step_index: int
    current_step_instruction: str
    last_steps_observations: List[str]
    fetched_data: Dict[str, Any]
    identified_risks: List[dict]
    
    # Sub-agent States
    planner_state: Dict[str, list]
    data_fetcher_state: Dict[str, Any]
    legal_analyst_state: Dict[str, Any]
    report_writer_state: Dict[str, Any]
    
    # Logs for Granular UI Streaming
    logs: Annotated[List[str], operator.add]
    
    # Final Output
    final_report: str
    
    
class SupervisorDecision(BaseModel):
    """Structured output for supervisor decisions"""
    next_agent: Literal["planner", "data_fetcher", "legal_analyst", "report_writer", "FINISH"] = Field(
        description="The next agent to invoke based on the plan and observations"
    )
    plan_item_index: int = Field(
        description="The index of the plan item being executed (0-based)"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )
    next_instruction: str = Field(
        description="The instruction for the next agent to execute"
    )


class ForcedStopSummary(BaseModel):
    """Structured output for forced stop summary"""
    summary: str = Field(
        description="A comprehensive summary of what was accomplished, what remains, and why the process was stopped"
    )
    key_findings: list[str] = Field(
        description="List of key findings or risks identified so far"
    )
    remaining_steps: list[str] = Field(
        description="List of plan steps that were not completed"
    )