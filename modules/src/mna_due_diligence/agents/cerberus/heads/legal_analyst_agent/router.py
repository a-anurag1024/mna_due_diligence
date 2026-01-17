from typing import Literal
from .types import AnalystState


def router_logic(state: AnalystState) -> Literal["tools", "force_exit", "end", "continue_reasoning", "conclude"]:
    messages = state["messages"]
    last_message = messages[-1]
    current_step = state.get("loop_step", 0)

    # 1. CHECK LIMIT
    if current_step >= 3:
        return "force_exit"

    # 2. CHECK NEXT_STEP PARAMETER (PRIMARY ROUTING)
    next_step = state.get("next_step", "")
    
    if next_step == "tool_call":
        # Check if there are actual tool calls in the message
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        # If no actual tool calls but next_step is tool_call, continue analysis
        return "continue_reasoning"
    
    if next_step == "conclude":
        return "conclude"
    
    if next_step == "continue_analysis":
        # Continue reasoning without tools
        return "continue_reasoning"
    
    # 3. FALLBACK: CHECK TOOL CALLS DIRECTLY (backward compatibility)
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"

    # 4. OTHERWISE, FINISH
    return "end"