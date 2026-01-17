from typing import TypedDict, List, Annotated, Optional
import operator
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class GateKeeperState(TypedDict):
    """
    The permanent memory of the chatbot session.
    """
    messages: Annotated[List[BaseMessage], operator.add] # Chat History
    risk_register: Annotated[List[dict], operator.add]   # Global List of Risks Found
    user_id: str