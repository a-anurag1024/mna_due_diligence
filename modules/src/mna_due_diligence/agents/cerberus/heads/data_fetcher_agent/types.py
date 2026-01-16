from pydantic import BaseModel, Field
from typing import Dict


class FetchedData(BaseModel):
    """Represents data fetched by the Data Fetcher Agent."""
    data: Dict[str, str] = Field(..., description="Key-value pairs of fetched data. The key is a representative tag (e.g., 'nda_files'), and the value is the fetched content or list.")