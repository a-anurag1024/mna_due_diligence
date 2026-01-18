from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from .hades import hades_subgraph

from .types import GateKeeperState


llm = ChatOpenAI(model="gpt-4.1-nano")

# --- GATEKEEPER NODE ---
def gatekeeper_node(state: GateKeeperState):
    """
    Analyzes user input to decide:
    1. Chat directly (simple queries, greetings).
    2. Invoke Hades (complex audit requests).
    """
    last_msg = state["messages"][-1].content
    
    # Simple Keyword/LLM Router
    system_prompt = """
    You are the Gatekeeper for the Cerberus Risk Engine.
    Classify the user's intent.
    - If they want to Find, Audit, Check, or Scan contracts -> Return 'INVOKE_HADES'.
    - If they say Hi, ask about capabilities, or refer to past chat -> Return 'REPLY_DIRECTLY'.
    """
    
    router_response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=last_msg)
    ])
    
    intent = router_response.content.strip()
    
    if "INVOKE_HADES" in intent:
        return {"action": "invoke_hades"}
    else:
        return {"action": "reply_directly"}



def direct_reply_node(state: GateKeeperState, config):
    """Standard RAG or Chat response without the heavy workflow."""
    # Broadcast Update
    logger = config.get('configurable', {}).get('logger')
    logger.log("Gatekeeper", "💬 Handling direct reply without Hades.")
    # This could check state["risk_register"] to answer questions about previous findings
    context = ""
    if state.get("risk_register"):
        context = f"CONTEXT: We previously found {len(state['risk_register'])} risks."
        
    response = llm.invoke(state["messages"] + [SystemMessage(content=context)])
    return {"messages": [response]}


def call_hades_wrapper(state: GateKeeperState, config):
    """
    Invokes the Hades Subgraph.
    Maps Parent State -> Child State -> Parent State.
    """
    logger = config.get('configurable', {}).get('logger')
    logger.log("Gatekeeper", "🚪 Invoking Hades Subgraph for deep audit...")
    
    user_input = state["messages"][-1].content
    
    # 1. Initialize Child State
    initial_state = {
        "mission": user_input,
        "plan": [],
        "current_step_index": 0,
        "fetched_data": {},
        "identified_risks": []
    }
    
    # 2. Run Subgraph (This blocks until Hades finishes OR pauses for HITL)
    # IMPORTANT: Pass config so logger is available to child nodes
    result = hades_subgraph.invoke(initial_state, config=config)
    
    # 3. Extract Results
    final_report = result.get("final_report", "Audit failed to generate report.")
    new_risks = result.get("identified_risks", [])
    
    # Log the risks found
    if logger:
        logger.log("Gatekeeper", f"✅ Hades completed. Found {len(new_risks)} risks.")
    
    # 4. Update Parent State
    return {
        "messages": [AIMessage(content=final_report)],
        "risk_register": new_risks # Add to global registry
    }