from mna_due_diligence.evals.party_wise import run_party_wise_evaluation


clause_types = {
    "ChangeOfControl": "Change Of Control",
    "AntiAssignment": "Anti-Assignment",
    "UnlimitedLiability": "Uncapped Liability",
    "NonCompete": "Non-Compete",
    "Exclusivity": "Exclusivity"
}

selected_clause_type = "UnlimitedLiability"
selected_clause = clause_types[selected_clause_type]
num_top_parties = 3

eval_report_file_path = f"./data/eval_reports/party_wise_evaluation_{selected_clause_type}_{num_top_parties}.json"

master_clause_csv_file = "./data/CUAD_v1/master_clauses_short.csv"

if __name__ == "__main__":
        
    run_party_wise_evaluation(
        clause_type=selected_clause,
        num_top_parties=num_top_parties,
        master_clause_csv_file=master_clause_csv_file,
        eval_report_file_path=eval_report_file_path
    )
