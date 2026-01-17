from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from ..tools.hitl import ask_human_tool

from .types import HadesState
from .nodes import planner_wrapper, fetcher_wrapper, analyst_wrapper, writer_wrapper
from .supervisor import supervisor_node


# --- BUILD THE SUBGRAPH ---
hades_builder = StateGraph(HadesState)

hades_builder.add_node("supervisor", supervisor_node)
hades_builder.add_node("planner", planner_wrapper)
hades_builder.add_node("data_fetcher", fetcher_wrapper)
hades_builder.add_node("legal_analyst", analyst_wrapper)
hades_builder.add_node("report_writer", writer_wrapper)
hades_builder.add_node("human_review", ask_human_tool)  # Using the HITL tool directly as a node

hades_builder.add_edge(START, "supervisor")

# Routing
hades_builder.add_conditional_edges(
    "supervisor",
    lambda x: x["next"], # The key returned by supervisor_node
    {
        "planner": "planner",
        "data_fetcher": "data_fetcher",
        "legal_analyst": "legal_analyst",
        "report_writer": "report_writer",
        "human_review": "human_review",
        "FINISH": END
    }
)

# Return edges
for node in ["planner", "data_fetcher", "legal_analyst", "report_writer", "human_review"]:
    hades_builder.add_edge(node, "supervisor")

hades_subgraph = hades_builder.compile()