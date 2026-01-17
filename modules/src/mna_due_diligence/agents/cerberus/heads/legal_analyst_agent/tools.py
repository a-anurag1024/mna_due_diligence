from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_human_tool(question: str) -> str:
    """
    Use this tool to ask the human user for clarification, business context, or approval.
    The question should have proper context to get a useful answer.
    The agent execution will PAUSE here until the human responds.
    """
    # This triggers the graph interrupt. The value returned by the human later 
    # will be injected as the return value of this function.
    human_answer = interrupt(question)
    return f"Human responded: {human_answer}"