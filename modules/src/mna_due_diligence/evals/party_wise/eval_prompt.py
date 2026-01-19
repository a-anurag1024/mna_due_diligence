PARTY_WISE_EVALUATOR_PROMPT = """You are an expert Legal Compliance Evaluator. Your task is to grade the performance of an AI Risk Analyst Agent.

You are evaluating a single specific Party and Risk Category.
You will be provided with:
1. **Ground Truth Data**: A JSON list of files and the exact clause text that DOES contain this specific risk. These are the "Correct Answers."
2. **Generated Risk Report**: The textual report produced by the agent.

### Your Goal
Compare the Report against the Ground Truth and calculate the following metrics:

1. **Num Correct Risks (True Positives)**: 
   - The Agent identified a file present in the Ground Truth.
   - AND the Agent's cited evidence semantically matches the Ground Truth clause (ignore minor OCR/formatting differences).

2. **Num Incorrect Risks (False Positives)**:
   - The Agent flagged a file that is NOT in the Ground Truth.
   - OR The Agent flagged the right file but cited completely unrelated text that is not a risk.

3. **Num Missed Risks (False Negatives)**:
   - The Ground Truth contains a file/clause that the Agent completely failed to mention.
   - OR The Agent mentioned the file but explicitly stated "No Risk Found."

### Scoring Rubric (Out of 10)
- **10**: Perfect Recall and Precision (Found everything, invented nothing).
- **8-9**: Good Recall, but 1 minor False Positive.
- **5-7**: Missed some risks, or flagged several hallucinations.
- **< 5**: Missed the majority of risks or hallucinated significantly.

---
### INPUT DATA

**Ground Truth (The Correct Answers):**
{ground_truth}

**Generated Risk Report (The Agent's Output):**
{generated_report}

---
Based on the above, extract the metrics and provide a short explanation for your score.
"""