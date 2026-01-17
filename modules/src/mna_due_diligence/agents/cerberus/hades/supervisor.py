from langchain_openai import ChatOpenAI

from .types import HadesState, SupervisorDecision, ForcedStopSummary, SupervisorDecision
from ..heads.planner_agent import AuditPlan


# --- SUPERVISOR LOGIC ---
def supervisor_node(state: HadesState):
    """
    Decides which head to activate next based on the plan using LLM-based decision making.
    Increments current_step_index and enforces a maximum of 6 steps.
    """
    # Broadcast Update
    print(f"[Hades Supervisor] Evaluating next agent at step {state.get('current_step_index', 0)}...")
    
    
    plan: AuditPlan = state.get("plan", [])
    idx = state.get("current_step_index", 0)
    last_observations = state.get("last_steps_observations", [])
    
    # Initialize LLM for decision making
    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    
    # 1. If no plan exists, call Planner (no increment yet)
    if not plan:
        return {"next": "planner", "current_step_index": 0}
    plan_str = "\n".join([f"{step.id}. {step.agent}: {step.instruction} dependencies: {step.dependency}" for step in plan.steps])
    
    # 2. Check if we've exceeded the maximum number of steps (6)
    
    if idx > 6:
        # Generate forced stop summary using LLM
        summary_llm = llm.with_structured_output(ForcedStopSummary)
        
        summary_prompt = f"""The audit process has been forcibly stopped after exceeding 6 steps.
        
Mission: {state.get('mission', 'N/A')}

Plan:
{plan_str}

Observations from completed steps:
{chr(10).join([f"Step {i+1}: {obs}" for i, obs in enumerate(last_observations)])}

Current step index: {idx}
Total plan steps: {len(plan.steps)}

Identified risks so far: {len(state.get('identified_risks', []))}

Generate a comprehensive summary of what was accomplished, what remains incomplete, and why the process was stopped."""
        
        summary_result = summary_llm.invoke(summary_prompt)
        
        # Create a forced stop report
        forced_report = f"""# FORCED STOP SUMMARY (Max Steps Exceeded)

{summary_result.summary}

## Key Findings:
{chr(10).join([f"- {finding}" for finding in summary_result.key_findings])}

## Remaining Steps:
{chr(10).join([f"- {step}" for step in summary_result.remaining_steps])}

## Recommendations:
- Review the plan to ensure efficiency
- Consider breaking down complex tasks into simpler steps
- Restart the process with a more focused mission if needed
"""
        
        return {
            "next": "FINISH",
            "final_report": forced_report,
            "logs": [f"Forced stop at step {idx}: exceeded maximum of 6 steps"]
        }
    
    # 3. If we finished all planned steps, write report (if not done)
    if idx >= len(plan.steps):
        if not state.get("final_report"):
            return {
                "next": "report_writer",
                "current_step_index": idx + 1
            }
        return {"next": "FINISH"}
    
    # 4. Use LLM to decide the next agent based on plan and observations
    decision_llm = llm.with_structured_output(SupervisorDecision)
    
    # Prepare context for LLM
    decision_prompt = f"""You are the supervisor of a multi-agent system conducting M&A due diligence.

Mission: {state.get('mission', 'N/A')}

Current Plan:
{plan_str}

Current Step Index: {idx} (0-based)
Current Plan Item: {plan.steps[idx]}

Recent Observations:
{chr(10).join([f"Step {i+1}: {obs}" for i, obs in enumerate(last_observations[-3:])]) if last_observations else "No observations yet"}

Based on the plan and observations, determine which agent should be invoked next and give the instruction for that agent.
Available agents: data_fetcher, legal_analyst, report_writer, planner, FINISH

Note: You should generally follow the plan unless observations suggest otherwise."""
    
    decision: SupervisorDecision = decision_llm.invoke(decision_prompt)
    
    # 5. Increment the step index
    new_idx = idx + 1
    
    # 6. Update current_step_instruction if we're executing a plan item
    updates = {
        "next": decision.next_agent,
        "current_step_index": new_idx,
        "logs": [f"Supervisor Decision (Step {new_idx}): {decision.reasoning}"]
    }
    
    # Set the current instruction if proceeding with a plan item
    if idx < len(plan.steps):
        updates["current_step_instruction"] = decision.next_instruction
    
    return updates