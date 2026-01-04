from pydantic import BaseModel, Field
from typing import Optional


class ContractMetadata(BaseModel):
    contract_title: str = Field(..., description="The main title, e.g., 'Master Services Agreement'")
    contract_type: str = Field(..., description="Classify into: NDA, MSA, SOW, License, Lease, Employment, IP, Service, Non-Compete, Maintenance, etc.")
    party_a: str = Field(..., description="Name of the first party/entity")
    party_b: str = Field(..., description="Name of the counter-party")
    effective_date: Optional[str] = Field(None, description="ISO 8601 format YYYY-MM-DD. If not found, return None.")
    expiration_date: Optional[str] = Field(None, description="ISO 8601 format or 'Perpetual'")
    governing_law: Optional[str] = Field(None, description="State or Country law, e.g., 'California', 'United Kingdom'")