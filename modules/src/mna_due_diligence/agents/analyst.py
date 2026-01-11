from pydantic_ai import Agent, RunContext

from .deps import WorkerDeps
from ..logging import truncate_for_log


analyst_agent = Agent(
    'openai:gpt-4.1-mini',
    deps_type=WorkerDeps,
    system_prompt="""
    You are the Data Decipherer. You read raw legal text and extract structured facts.
    You will be given a filename. You must READ it and extract the requested data.
    """
)

@analyst_agent.tool
async def read_document(ctx: RunContext[WorkerDeps], filename: str) -> str:
    """Read the full text of a document."""
    try:
        # Log the MCP tool call
        if ctx.deps.logging_service:
            async with ctx.deps.logging_service.log_tool_execution(
                tool_name="read_file",
                tool_type="mcp",
                input_arguments={"filename": filename}
            ) as log_id:
                # Call the MCP tool
                result = await ctx.deps.client.session.call_tool("read_file", arguments={"filename": filename})
                
                # Extract content from result
                content = result.content[0].text if result.content else str(result)
                
                # Update tool log with result (truncated for logging)
                await ctx.deps.logging_service.update_tool_log(
                    log_id=log_id,
                    output_result=truncate_for_log(content)
                )
                return content
        else:
            # Fallback if no logging service
            result = await ctx.deps.client.session.call_tool("read_file", arguments={"filename": filename})
            return result.content[0].text if result.content else str(result)
    except Exception as e:
        error_msg = f"Error reading document '{filename}': {str(e)}"
        if ctx.deps.logging_service:
            await ctx.deps.logging_service.update_tool_log(
                log_id=log_id,
                output_result=error_msg
            )
        return error_msg