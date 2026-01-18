from langchain_openai import ChatOpenAI

from mna_due_diligence.agents.cerberus.heads.data_fetcher_agent import data_fetcher_node
from mna_due_diligence.agents.cerberus.heads.planner_agent import planner_node
from mna_due_diligence.agents.cerberus.heads.legal_analyst_agent import legal_analyst_node
from mna_due_diligence.agents.cerberus.heads.report_writer import report_writer_node

from .types import HadesState, SupervisorDecision, ForcedStopSummary


# --- WRAPPER NODES (Connecting Heads to State) ---

def planner_wrapper(state: HadesState, config):
    """Calls the Planner Head"""
    # Broadcast Update
    print(f"[Hades Planner Wrapper] Invoking planner for mission: {state['mission']}...")
    
    logger = config.get('configurable', {}).get('logger')
    result = planner_node(state['mission'], logger)
    observation = f"Plan for the mission: \n{result['plan']}"
    return {
        "plan": result['plan'],
        "last_steps_observations": state.get("last_steps_observations", []) + [observation]
    }


def fetcher_wrapper(state: HadesState, config):
    """Calls the Data Fetcher Head"""
    # Broadcast Update
    print(f"[Hades Data Fetcher Wrapper] Invoking data fetcher for instruction: {state['current_step_instruction']}...")
    
    logger = config.get('configurable', {}).get('logger')
    result = data_fetcher_node(state['current_step_instruction'], logger)
    observation = result.get("message", "No message returned.")
    if state.get('data_fetcher_state', None) is None:
        state['data_fetcher_state'] = []
    if state.get('last_steps_observations', None) is None:
        state['last_steps_observations'] = []
    return {
        "fetched_data": result['fetched_data'],
        "last_steps_observations": state.get("last_steps_observations", []) + [observation]
    }


def analyst_wrapper(state: HadesState):
    """Calls the Legal Analyst Head"""
    # Broadcast Update
    print(f"[Hades Legal Analyst Wrapper] Invoking legal analyst for instruction: {state['current_step_instruction']}...")
    
    result = legal_analyst_node(instruction=state['current_step_instruction'],
                                data=state['fetched_data'],
                                older_messages=state.get('legal_analyst_state', {}).get('messages', []),
                                config=state.get('legal_analyst_state', {}).get('config', None))
    observation = result.get("final_summary", "No summary provided.")
    if result.get('data_requirements', []):
        observation += f"\n Additional Data requirements requested: {len(result['data_requirements'])}."
        for req in result['data_requirements']:
            description = req.description
            purpose = req.purpose
            plan_after_data = req.plan_after_data
            observation += f"\n - {description}: {purpose}. Next steps: {plan_after_data}"
    if state.get('legal_analyst_state', None) is None:
        state['legal_analyst_state'] = {}
    messages = state.get('legal_analyst_state', {}).get('messages', []) + result.get("messages", [])
    if state.get('last_steps_observations', None) is None:
        state['last_steps_observations'] = []
    return {
        "identified_risks": state.get("identified_risks", []) + result['new_risks'],
        "legal_analyst_state": {
            "messages": messages,
            "config": result.get("config", None)
        },
        "last_steps_observations": state.get("last_steps_observations", []) + [observation]
    }


def writer_wrapper(state: HadesState, config):
    """Calls the Report Writer Head"""
    # Broadcast Update
    print(f"[Hades Report Writer Wrapper] Invoking report writer for mission: {state['mission']}...")
    
    logger = config.get('configurable', {}).get('logger')
    result = report_writer_node(
        mission=state['mission'],
        risks=state['identified_risks'],
        logger=logger
    )
    if state.get('report_writer_state', None) is None:
        state['report_writer_state'] = []
    return {
        "final_report": result['final_report'],
        "last_steps_observations": state.get("last_steps_observations", []) + [result['final_report']]
    }