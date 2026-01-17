from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt
from langchain_core.messages import SystemMessage, HumanMessage

from .types import AnalystState, RiskFinding, DataRequirement
from .nodes import reasoner_node, tool_node, forced_conclusion_node, conclusion_node
from .router import router_logic
from .prompts import ANALYST_SYSTEM_PROMPT, REASONER_SYSTEM_PROMPT

# --- BUILD GRAPH ---
workflow = StateGraph(AnalystState)

# Define Nodes
workflow.add_node("reasoner", reasoner_node)
workflow.add_node("tools", tool_node)
workflow.add_node("force_exit", forced_conclusion_node)
workflow.add_node("conclude", conclusion_node)

# Entry Point
workflow.add_edge(START, "reasoner")

# Conditional Edge from Reasoner
workflow.add_conditional_edges(
    "reasoner",
    router_logic,
    {
        "tools": "tools",       # Go run tools
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

# Edge from Force Exit to End
workflow.add_edge("force_exit", END)
# Edge from Conclude to End
workflow.add_edge("conclude", END)

# Compile with checkpointer for Human-in-the-Loop support
memory = MemorySaver()
legal_analyst_graph = workflow.compile(checkpointer=memory)


#  ---- Legal Analyst Agent (Standalone) ----

def legal_analyst_standalone(instruction: str, 
                            data: dict[str, str],
                            older_messages: list = None,
                            config: dict = None,
                            resume_value = None) -> dict:
    # Prepare Context
    # We format the fetched data into a readable prompt
    context_str = f"TASK: {instruction}\n\nAVAILABLE DATA:\n"
    for key, val in data.items():
        # Truncate very long values for token efficiency if needed
        val_str = str(val)
        if len(val_str) > 5000: 
            val_str = val_str[:5000] + "...[truncated]"
        context_str += f"--- {key} ---\n{val_str}\n\n"

    # Setup config for checkpointing
    if config is None:
        # Generate a unique thread_id if not provided
        import uuid
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    # If resuming from an interrupt, send the resume command
    if resume_value is not None:
        result = legal_analyst_graph.invoke(
            Command(resume=resume_value),
            config=config
        )
    else:
        # Initial invocation - Run the Graph
        # We initialize loop_step to 0 and new fields
        if older_messages is None:
            older_messages = []
        inputs = {
            "messages": older_messages[-5:] + [
                SystemMessage(content=REASONER_SYSTEM_PROMPT),
                HumanMessage(content=context_str)
            ],
            "loop_step": 0,
            "new_risks": [],
            "data_requirements": [],
            "next_step": "continue_analysis"
        }
        
        # invoke() runs until END or interrupt
        result = legal_analyst_graph.invoke(inputs, config=config)
    
    # Check if execution was interrupted (HITL)
    # Get the current state to check for interrupts
    state_snapshot = legal_analyst_graph.get_state(config)
    is_interrupted = len(state_snapshot.next) > 0  # If there are pending nodes, it's interrupted
    
    # Extract accumulated data from the state
    risk_findings = result.get("new_risks", [])
    data_requirements = result.get("data_requirements", [])
    messages = result.get("messages", [])
    
    # Convert Pydantic models to dicts if needed
    risk_findings_list = []
    for risk in risk_findings:
        if isinstance(risk, RiskFinding):
            risk_findings_list.append(risk.model_dump())
        elif isinstance(risk, dict):
            risk_findings_list.append(risk)
        else:
            risk_findings_list.append(risk)
    
    data_requirements_list = []
    for req in data_requirements:
        if isinstance(req, DataRequirement):
            data_requirements_list.append(req.model_dump())
        elif isinstance(req, dict):
            data_requirements_list.append(req)
        else:
            data_requirements_list.append(req)
    
    # Return structured output with interrupt information
    output = {
        "risk_findings": risk_findings_list,
        "data_requirements": data_requirements_list,
        "messages": messages,
        "is_interrupted": is_interrupted,
        "config": config  # Return config so caller can resume
    }
    
    # If interrupted, include the interrupt information
    if is_interrupted:
        # Get the interrupt value (the question asked by ask_human_tool)
        tasks = state_snapshot.tasks
        if tasks:
            # The interrupt value is in the task's interrupts
            for task in tasks:
                if hasattr(task, 'interrupts') and task.interrupts:
                    output["interrupt_question"] = task.interrupts[0].value
                    break
    
    return output