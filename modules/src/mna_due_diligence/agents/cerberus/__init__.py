from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .types import GateKeeperState
from .nodes import gatekeeper_node, direct_reply_node, call_hades_wrapper

# --- BUILD THE WORKFLOW ---
workflow = StateGraph(GateKeeperState)

workflow.add_node("gatekeeper", gatekeeper_node)
workflow.add_node("direct_chat", direct_reply_node)
workflow.add_node("hades_engine", call_hades_wrapper)

workflow.add_edge(START, "gatekeeper")

workflow.add_conditional_edges(
    "gatekeeper",
    lambda x: x["action"], # Based on gatekeeper logic
    {
        "reply_directly": "direct_chat",
        "invoke_hades": "hades_engine"
    }
)

workflow.add_edge("direct_chat", END)
workflow.add_edge("hades_engine", END)

# CRITICAL: We need memory for the PARENT so it can handle the Child's interrupts
memory = MemorySaver()
cerberus_agent = workflow.compile(checkpointer=memory)