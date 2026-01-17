from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt
import json
from .types import AnalystOutput

from .tools import ask_human_tool
from .types import AnalystState, ReasonerOutput, RiskFinding, DataRequirement

# --- CONFIG ---
llm = ChatOpenAI(model="gpt-4.1-mini")
tools = [ask_human_tool]
# Bind tools to LLM so it knows it can use them
llm_with_tools = llm.bind_tools(tools)
# LLM with structured output for reasoning
llm_structured = llm.with_structured_output(ReasonerOutput)


# --- NODE 1: THE REASONER ---
def reasoner_node(state: AnalystState):
    """
    Decides the next step with structured output.
    Returns new_risks, summary, next_step, and data_requirements.
    """
    # Broadcast Update
    print(f"[Legal Analyst] Reasoning step {state.get('loop_step', 0)}...")
    # First check if we should call tools
    # We use llm_with_tools to detect tool call needs
    tool_check_response = llm_with_tools.invoke(state["messages"])
    
    # If the LLM wants to call a tool, return immediately
    if hasattr(tool_check_response, 'tool_calls') and tool_check_response.tool_calls:
        return {
            "messages": [tool_check_response],
            "new_risks": [],
            "data_requirements": [],
            "next_step": "tool_call"
        }
    
    # Otherwise, get structured reasoning output
    try:
        reasoner_output: ReasonerOutput = llm_structured.invoke(state["messages"])
        
        # Format data requirements for display
        data_req_str = ""
        if reasoner_output.data_requirements:
            data_req_str = "\n\n**Data Requirements:**\n"
            for req in reasoner_output.data_requirements:
                data_req_str += f"- {req.description} (Purpose: {req.purpose})\n"
        
        # Create a formatted message with the analysis update
        formatted_response = AIMessage(content=f"""
**Analysis Update:**
{reasoner_output.summary}
**Next Step:** {reasoner_output.next_step}
""")
        
        return {
            "messages": [formatted_response],
            "new_risks": reasoner_output.new_risks,
            "data_requirements": reasoner_output.data_requirements,
            "next_step": reasoner_output.next_step
        }
    except Exception as e:
        # Fallback if structured output fails
        fallback_msg = AIMessage(content=f"Error in structured reasoning: {str(e)}. Continuing analysis...")
        return {
            "messages": [fallback_msg],
            "new_risks": [],
            "data_requirements": [],
            "next_step": "continue_analysis"
        }


# --- NODE 2: THE TOOL EXECUTOR ---
# We use LangGraph's prebuilt ToolNode for simplicity
tool_node = ToolNode(tools)


# --- NODE 3: FORCED CONCLUSION (The Safety Net) ---
def forced_conclusion_node(state: AnalystState):
    """
    Called when the agent runs out of steps. 
    Forces a valid output with all accumulated risks and a summary.
    """
    # Broadcast Update
    print(f"[Legal Analyst] Forced conclusion at step {state.get('loop_step', 0)}.")
    
    # Collect all accumulated risks from state
    all_risks = state.get("new_risks", [])
    
    # Give a brief summary based on what was done so far
    analysis_summary = f"Analysis terminated after {state['loop_step']} steps. "
    analysis_summary += f"Found {len(all_risks)} total risks. "
    
    # Get data requirements if any
    data_reqs = state.get("data_requirements", [])
    if data_reqs:
        analysis_summary += f"{len(data_reqs)} data requirements pending. "
    
    final_output = AnalystOutput(
        findings=all_risks,
        analysis_summary=analysis_summary
    )
    
    # We return this as a final AIMessage so the wrapper can parse it
    return {
        "messages": [AIMessage(content=f"Analysis concluded with {len(all_risks)} findings.")],
        "final_output": final_output.model_dump()
    }


# --- NODE 4: NATURAL CONCLUSION ---
def conclusion_node(state: AnalystState):
    """
    Called when the agent naturally completes analysis.
    Compiles all accumulated risks into final output.
    """
    # Broadcast Update
    print(f"[Legal Analyst] Natural conclusion at step {state.get('loop_step', 0)}.")
    
    # Collect all accumulated risks from state
    all_risks = state.get("new_risks", [])
    
    # Get the last message summary
    last_msg = state["messages"][-1].content if state["messages"] else ""
    
    # Create comprehensive summary
    analysis_summary = f"Analysis completed after {state['loop_step']} steps. "
    analysis_summary += f"Identified {len(all_risks)} total risks. "
    
    # Check data requirements
    data_reqs = state.get("data_requirements", [])
    if data_reqs:
        analysis_summary += f"Note: {len(data_reqs)} data requirements were identified. "
    
    final_output = AnalystOutput(
        findings=all_risks,
        analysis_summary=analysis_summary
    )
    
    return {
        "messages": [AIMessage(content=f"✓ Analysis complete. Found {len(all_risks)} findings.")],
        "final_output": final_output.model_dump()
    }