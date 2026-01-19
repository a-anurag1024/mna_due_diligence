# Cerberus Agent Evaluation Summary  
**Dataset:** CUAD (100-file subset)  
**Date of Evaluation:** 19/01/2026  

## Overview
This report summarizes the Cerebus agent’s performance in identifying key legal risk categories across the **top 2–3 parties with the highest number of documents** containing such risks. The evaluation emphasizes precision and recall at the clause-type level.

## Clause-Level Performance

| Clause Type          | Parties Evaluated | Precision | Recall |
|----------------------|-------------------|-----------|--------|
| Anti-Assignment      | 2                 | 66%       | 100%   |
| Change of Control    | 3                 | 75%       | 100%   |
| Unlimited Liability  | 3                 | 71%       | 100%   |

## Aggregate Metrics
- **Total Precision:** 70%  
- **Total Recall:** 100%  
- **LLM-as-a-Judge Score:** 8.5 / 10  

## Key Takeaways
- The Cerberus agent achieved **perfect recall across all evaluated clause types**, ensuring no ground-truth risks were missed.
- Precision varied by clause type, with **Change of Control** performing strongest.
- Overall performance indicates a **reliable risk coverage model** with moderate false positives, suitable for high-recall legal risk screening workflows.
