from mna_due_diligence.agents.cerberus.hades import hades_subgraph, hades_builder
from langgraph.checkpoint.memory import MemorySaver

from .evaluator import evaluate_agent_output
from .gt_data import create_gt_data


def run_hades_subgraph(mission: str):
    """Utility to run the Hades subgraph standalone for testing."""
    memory = MemorySaver()
    hades_with_memory = hades_builder.compile(checkpointer=memory)

    config = {"configurable": {"thread_id": "hades_test_session"}}
    results = hades_with_memory.invoke({"mission": mission}, config=config)
    return results


def save_eval_report(eval_report: dict, eval_report_file_path: str):
    """Utility to save the evaluation report to a JSON file."""
    import json
    with open(eval_report_file_path, 'w') as f:
        json.dump(eval_report, f, indent=4)


def run_party_wise_evaluation(clause_type: str,
                              num_top_parties: int,
                              master_clause_csv_file: str,
                              eval_report_file_path: str) -> dict:
    """Utility to run the party-wise evaluation."""
    eval_report = {}
    
    print(f"[EVAL] Generating ground-truth data for clause type: {clause_type}...")
    gt_data = create_gt_data(clause_type=clause_type,
                             master_clause_csv_file=master_clause_csv_file,
                             number_of_top_parties=num_top_parties)
    
    
    eval_report['ground_truth'] = gt_data
    eval_report['results'] = {}
    save_eval_report(eval_report, eval_report_file_path)
    
    
    for party, gt_data in gt_data.items():
        print(f"\n\n[EVAL] Running Hades subgraph for party: {party}...")
        mission = f"Identify and summarize all risks related to '{clause_type}' clauses for party '{party}'. DONOT PAUSE FOR HUMAN INPUT. PROVIDE ANSWER DIRECTLY BASED ON YOUR KNOWLEDGE and agency."
        hades_response = run_hades_subgraph(mission=mission)
        
        final_report = hades_response.get("final_report", "")
        eval_report['results'][party] = {"agent_generated_report": final_report}
        save_eval_report(eval_report, eval_report_file_path)
        
        print(f"[EVAL] Evaluating agent output for party: {party}...")
        report_card = evaluate_agent_output(generated_risk_report=final_report,
                                            ground_truth_data=gt_data)
        
        eval_report['results'][party]['evaluation'] = report_card.model_dump(mode='json')
        save_eval_report(eval_report, eval_report_file_path)