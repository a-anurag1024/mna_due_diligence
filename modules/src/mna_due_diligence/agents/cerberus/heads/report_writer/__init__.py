import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from .prompt import REPORT_WRITER_PROMPT


# --- CONFIG ---
llm = ChatOpenAI(model="gpt-4.1-nano")


def report_writer_node(mission: str,
                       risks: list[dict],
                       logs: list):
    """
    Synthesizes the accumulated findings into a final Markdown report.
    """
    # Broadcast Update
    print(f"[Report Writer] Generating final report with {len(risks)} findings...")
    
    # 1. Check for "Empty" State (Safety Check)
    if not risks:
        no_risk_msg = (
            f"### 🛡️ Audit Report: {mission}\n\n"
            "**Status:** Clean\n\n"
            "**Executive Summary:**\n"
            "No material risks were identified in the documents processed. "
            "The Legal Analyst reviewed the fetched data and found no clauses meeting the risk criteria."
        )
        return {
            "final_report": no_risk_msg,
            "logs": ["📝 [Reporter] Generated 'No Risks' report."]
        }

    # 2. Prepare the Prompt
    risks_str = json.dumps(risks, indent=2)
    
    user_content = f"""
    **MISSION:** {mission}
    
    **IDENTIFIED RISKS:**
    {risks_str}
    
    **LOGS (Context):**
    {len(logs)} steps executed.
    
    Generate the Final Report now.
    """

    # 3. Invoke LLM
    # We don't need structured output here; we want a nice Markdown string.
    messages = [
        SystemMessage(content=REPORT_WRITER_PROMPT),
        HumanMessage(content=user_content)
    ]
    
    response = llm.invoke(messages)
    report_text = response.content

    # 5. Update State
    return {
        "final_report": report_text,
        "logs": [f"📝 [Reporter] Finalized report with {len(risks)} findings."]
    }