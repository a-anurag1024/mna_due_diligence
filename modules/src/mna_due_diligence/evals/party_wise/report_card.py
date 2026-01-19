from pydantic import BaseModel, Field
from typing import List, Dict

class PartyWiseEvalResult(BaseModel):
    num_of_correct_risks_identified: int = Field(
        ..., description="Number of risks correctly identified for the given party and risk category."
    )
    num_of_incorrect_risks_identified: int = Field(
        ..., description="Number of risks incorrectly identified for the given party and risk category."
    )
    num_of_missed_risks: int = Field(
        ..., description="Number of risks that were present in the ground truth but missed by the agent."
    )
    evaluation_score: float = Field(
        ..., description="Overall evaluation score for the party and risk category (out of 10)."
    )
    short_explanation: str = Field(
        ..., description="A brief explanation of the evaluation results."
    )