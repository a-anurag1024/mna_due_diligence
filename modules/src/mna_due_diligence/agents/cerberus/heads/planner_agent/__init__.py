from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from .types import AuditPlan
from .prompt import PLANNER_PROMPT



llm = ChatOpenAI(model="gpt-4.1-mini")



def planner_node(mission: str) -> dict:
    """
    The Planner Node. 
    Reads the 'mission' and generates a structured 'AuditPlan'.
    Args:
        mission (str): High-level user mission for the audit.
    Returns:
        dict: {"plan": AuditPlan, "logs": List of log messages}
    """
    # Broadcast
    print(f"[Node] Planner Invoked with mission: {mission}")
    
    prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
    
    # 1. ENABLE RAW OUTPUT
    # This changes the return type from 'AuditPlan' to a dict: 
    # {'parsed': AuditPlan, 'raw': AIMessage, ...}
    planner = prompt | llm.with_structured_output(AuditPlan, include_raw=True)
    
    # 2. Invoke
    result = planner.invoke({"mission": mission})
    
    # 3. Unpack Results
    plan_obj = result["parsed"]
    raw_message: AIMessage = result["raw"]
    
    # 4. Extract Token Usage
    # Recent LangChain versions normalize this into .usage_metadata
    # format: {'input_tokens': int, 'output_tokens': int, 'total_tokens': int}
    usage = raw_message.usage_metadata 
    
    # Fallback for older versions if usage_metadata is missing
    if not usage:
        usage = raw_message.response_metadata.get("token_usage", {})

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    
    # 5. Log it
    log_msg = (
        f"📅 Planner: Created {len(plan_obj.steps)} steps. "
        f"[Tokens: In={input_tokens}, Out={output_tokens}]"
    )

    return {
        "plan": plan_obj,
        "logs": [log_msg]
    }