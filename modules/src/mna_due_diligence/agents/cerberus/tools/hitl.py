from langchain_core.tools import tool
from langgraph.types import interrupt, Command


@tool
def ask_human_tool(question: str) -> str:
    """
    Use this tool to ask the human for clarification, approval, or missing data.
    The execution will PAUSE here until the human responds.
    """
    # This sends 'question' to the user and halts execution.
    # The value returned by the user (via Command(resume=...)) becomes 'human_answer'.
    human_answer = interrupt(question)
    
    return f"Human responded: {human_answer}"