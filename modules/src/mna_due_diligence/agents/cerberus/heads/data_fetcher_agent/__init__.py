from langgraph.graph import StateGraph, START, END

from .nodes import strategist_node, executor_node, forced_ending_node
from .types import FetcherState


def route_logic(state: FetcherState):
    """
    Decides whether to loop back, force end, or finish normally.
    """
    # 1. Hard Limit Check
    if state["iteration_count"] >= 3:
        return "force_end"
    
    # 2. Logic Check (Did the Strategist say we are done?)
    # If we have a final summary, we are likely done.
    # Alternatively, check if pending_tool_calls was empty (handled in strategist logic).
    if state.get("final_summary"):
        return "finish"
        
    # 3. Default: Loop back
    return "continue"



# --- BUILD GRAPH ---
workflow = StateGraph(FetcherState)

workflow.add_node("strategist", strategist_node)
workflow.add_node("executor", executor_node)
workflow.add_node("forced_ending", forced_ending_node)

# Flow
workflow.add_edge(START, "strategist")

# Conditional Logic after strategist: route to executor if there are pending tool calls, otherwise finish
workflow.add_conditional_edges(
    "strategist",
    lambda x: "executor" if x["pending_tool_calls"] else "finish",
    {
        "executor": "executor",
        "finish": END
    }
)

# Conditional Logic after executor: check iteration limit, then loop back to strategist, force end, or finish
workflow.add_conditional_edges(
    "executor",
    route_logic,
    {
        "continue": "strategist",
        "force_end": "forced_ending",
        "finish": END
    }
)

# Forced ending always goes to END
workflow.add_edge("forced_ending", END)

data_fetcher_agent = workflow.compile()


def data_fetcher_node(instruction: str, logger=None) -> dict:
    """
    Executes the Data Fetcher State Graph for the given instruction.
    
    Args:
        instruction: The instruction for data fetching
        logger: CerberusMindLogger instance for logging
    """
    # 1. Broadcast Update
    print(f"[Node] Data Fetcher Invoked with instruction: {instruction}")
    
    # 2. Initial State
    initial_state: FetcherState = {
        "instruction": instruction,
        "iteration_count": 0,
        "fetched_data": {},
        "tool_logs": [],
        "pending_tool_calls": [],
        "final_summary": ""
    }
    
    # 3. Run the State Graph
    final_state = data_fetcher_agent.invoke(initial_state)
    
    # 4. Log and Return
    if logger:
        logger.log(
            "Data Fetcher",
            f"📥 Fetched {len(final_state['fetched_data'])} items in {final_state['iteration_count']} iterations."
        )
    
    final_message = f"📝 Summary: {final_state['final_summary']}"
    final_message += "\nTool logs:"
    final_message += "\n".join(final_state["tool_logs"])
    
    return {
        "fetched_data": final_state["fetched_data"],
        "message": final_message
    }