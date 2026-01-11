from pydantic_ai import Agent, RunContext

from .deps import WorkerDeps
from ..logging import truncate_for_log

rag_agent = Agent(
    'openai:gpt-4.1-mini',
    deps_type=WorkerDeps,
    system_prompt="""
    You are the RAG Scout. Your job is to find RELEVANT documents.
    Don't just search once. If the first search fails, try synonyms.
    Return a list of specific filenames and quote snippets.
    """
)

@rag_agent.tool
async def search_vdr(ctx: RunContext[WorkerDeps], query: str) -> str:
    """Search the vector database for clauses."""
    try:
        # Log the MCP tool call
        if ctx.deps.logging_service:
            async with ctx.deps.logging_service.log_tool_execution(
                tool_name="search_clauses",
                tool_type="mcp",
                input_arguments={"query": query}
            ) as log_id:
                # Call the MCP tool via the passed client
                result = await ctx.deps.client.session.call_tool("search_clauses", arguments={"query": query})
                
                # Extract content from result
                content = result.content[0].text if result.content else str(result)
                
                # Update tool log with result
                await ctx.deps.logging_service.update_tool_log(
                    log_id=log_id,
                    output_result=truncate_for_log(content)
                )
                return content
        else:
            # Fallback if no logging service
            result = await ctx.deps.client.session.call_tool("search_clauses", arguments={"query": query})
            return result.content[0].text if result.content else str(result)
    except Exception as e:
        error_msg = f"Error searching VDR: {str(e)}"
        if ctx.deps.logging_service:
            await ctx.deps.logging_service.update_tool_log(
                log_id=log_id,
                output_result=error_msg
            )
        return error_msg