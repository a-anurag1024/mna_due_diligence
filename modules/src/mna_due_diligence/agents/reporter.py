from pydantic_ai import Agent, RunContext

from .deps import WorkerDeps


writer_agent = Agent(
    'openai:gpt-4o',
    system_prompt="""
    You are the Reporting Officer. 
    Take the raw findings and format them into a strict Risk Report.
    Do not add new facts. Just format nicely with '## Risk' headers.
    """
)