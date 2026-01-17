from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langchain_core.messages import SystemMessage, HumanMessage

from .types import AnalystState, RiskFinding, DataRequirement
from .nodes import reasoner_node, expand_given_data, tool_node, forced_conclusion_node, conclusion_node
from .router import router_logic
from .prompts import ANALYST_SYSTEM_PROMPT, REASONER_SYSTEM_PROMPT

# --- BUILD GRAPH ---
workflow = StateGraph(AnalystState)

# Define Nodes
workflow.add_node("reasoner", reasoner_node)
workflow.add_node("tools", tool_node)
workflow.add_node("force_exit", forced_conclusion_node)
workflow.add_node("conclude", conclusion_node)
workflow.add_node("expand_given_data", expand_given_data)

# Entry Point
workflow.add_edge(START, "reasoner")

# Conditional Edge from Reasoner
workflow.add_conditional_edges(
    "reasoner",
    router_logic,
    {
        "tools": "tools",       # Go run tools
        "expand_given_data": "expand_given_data",  # Expand given data keys
        "force_exit": "force_exit", # Limit hit! Go to safety net
        "continue_reasoning": "step_counter",  # Continue reasoning loop
        "conclude": "conclude",  # Natural conclusion
        "end": END              # Natural finish (legacy)
    }
)

# Edge from Tools back to Reasoner (The Loop)
# CRITICAL: We increment the step count here
def increment_step(state: AnalystState):
    return {"loop_step": state.get("loop_step", 0) + 1}

workflow.add_node("step_counter", increment_step)
workflow.add_edge("tools", "step_counter")
workflow.add_edge("step_counter", "reasoner")
workflow.add_edge("expand_given_data", "step_counter")

# Edge from Force Exit to End
workflow.add_edge("force_exit", END)
# Edge from Conclude to End
workflow.add_edge("conclude", END)

# Compile with checkpointer for Human-in-the-Loop support
memory = MemorySaver()
legal_analyst_graph = workflow.compile(checkpointer=memory)



# --- Legal Analyst Node ---


def legal_analyst_node(instruction: str,
                       data: dict[str, str],
                       older_messages: list,
                       config: dict = None) -> dict:
    # Prepare Context
    context_str = f"TASK: {instruction}\n\nAVAILABLE DATA KEYS:\n"
    for key, val in data.items():
        context_str += f"--- {key} ---\n{val[:25]}...\n\n"
    
    if older_messages is None:
        older_messages = []
        
    inputs = {
        "messages": older_messages[-5:] + [
            SystemMessage(content=REASONER_SYSTEM_PROMPT),
            HumanMessage(content=context_str)
        ],
        "loop_step": 0,
        "input_data": data,
        "new_risks": [],
        "data_requirements": [],
        "next_step": "continue_analysis"
    }
    
    # invoke() runs until END or interrupt
    result = legal_analyst_graph.invoke(inputs, config=config)
    
    new_risks = [risk.model_dump(mode='json') for risk in result.get("new_risks", [])]
    
    return {
        "messages": result.get("messages", []),
        "new_risks": new_risks,
        "data_requirements": result.get("data_requirements", []),
        "final_summary": result.get("final_output", {}).get("analysis_summary", ""),
        "config": config  # Return config so caller can resume if needed
    }