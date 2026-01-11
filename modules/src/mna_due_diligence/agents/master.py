import asyncio
from pydantic_ai import Agent, RunContext
from mcp import ClientSession
from mcp.client.sse import sse_client
import httpx

from .analyst import analyst_agent
from .deps import WorkerDeps
from .RAG import rag_agent
from .reporter import writer_agent
from ..logging import create_logging_service, truncate_for_log

from .utils import extract_usage_from_result


def stream_final_answer(text: str):
    lines = [
        "=" * 60,
        "🎯 ✨ FINAL ANSWER ✨ 🎯",
        "=" * 60,
        "",
        *text.strip().splitlines(),
        "",
        "=" * 60,
    ]
    return lines


# --- DEPENDENCIES ---
class MasterDeps:
    def __init__(self, mcp_session, status_callback, logging_service=None):
        self.mcp_session = mcp_session
        self.status_callback = status_callback # Function to update Streamlit UI
        self.logging_service = logging_service or create_logging_service()
        # We create worker deps here to pass the session down
        self.worker_deps = WorkerDeps(self, self.logging_service) 

    @property
    def session(self):
        return self.mcp_session


# --- THE MASTER AGENT ---
master_agent = Agent(
    'openai:gpt-4.1-mini',
    deps_type=MasterDeps,
    system_prompt="""
    You are the Audit Lead. Manage the team to answer the user's request.
    1. Delegate search tasks to the RAG Scout.
    2. Delegate text analysis to the Decipherer.
    3. Delegate formatting to the Reporter.
    
    Always explain your plan before calling a worker.
    Always give final answers in a concise manner.
    """
)

# --- TOOLS: CALLING WORKERS ---
@master_agent.tool
async def call_rag_scout(ctx: RunContext[MasterDeps], instructions: str) -> str:
    """Send a task to the RAG Scout Agent."""
    ctx.deps.status_callback(f"🕵️‍♂️ RAG Scout is searching: {instructions}...")
    
    # Log the tool call
    async with ctx.deps.logging_service.log_tool_execution(
        tool_name="call_rag_scout",
        tool_type="agent_call",
        input_arguments={"instructions": instructions}
    ) as tool_log_id:
        # Log the agent execution
        async with ctx.deps.logging_service.log_agent_execution(
            agent_name="rag_agent",
            agent_role="RAG Scout",
            input_prompt=instructions,
            model_name=rag_agent.model
        ) as agent_log_id:
            # Run the sub-agent
            result = await rag_agent.run(instructions, deps=ctx.deps.worker_deps)
            
            # Extract token usage
            usage = extract_usage_from_result(result)
            
            # Update agent log with output and usage
            await ctx.deps.logging_service.update_agent_log(
                log_id=agent_log_id,
                output_response=truncate_for_log(result.output),
                total_tokens=usage['total_tokens'],
                prompt_tokens=usage['prompt_tokens'],
                completion_tokens=usage['completion_tokens']
            )
            
            # Stream the sub-agent response
            ctx.deps.status_callback(f"✅ RAG Scout found: {truncate_for_log(result.output)[:200]}...")
            
        # Update tool log with result
        await ctx.deps.logging_service.update_tool_log(
            log_id=tool_log_id,
            output_result=truncate_for_log(result.output)
        )
        
        return result.output

@master_agent.tool
async def call_decipherer(ctx: RunContext[MasterDeps], instructions: str, filename: str) -> str:
    """Send a task to the Decipher Analyst Agent."""
    ctx.deps.status_callback(f"🧐 Decipherer is reading {filename}...")
    
    # Log the tool call
    async with ctx.deps.logging_service.log_tool_execution(
        tool_name="call_decipherer",
        tool_type="agent_call",
        input_arguments={"instructions": instructions, "filename": filename}
    ) as tool_log_id:
        # Log the agent execution
        prompt = f"File: {filename}\nTask: {instructions}"
        async with ctx.deps.logging_service.log_agent_execution(
            agent_name="analyst_agent",
            agent_role="Decipherer",
            input_prompt=prompt,
            model_name=analyst_agent.model
        ) as agent_log_id:
            # Run the sub-agent
            result = await analyst_agent.run(prompt, deps=ctx.deps.worker_deps)
            
            # Extract token usage
            usage = extract_usage_from_result(result)
            
            # Update agent log with output and usage
            await ctx.deps.logging_service.update_agent_log(
                log_id=agent_log_id,
                output_response=truncate_for_log(result.output),
                total_tokens=usage['total_tokens'],
                prompt_tokens=usage['prompt_tokens'],
                completion_tokens=usage['completion_tokens']
            )
            
            # Stream the sub-agent response
            ctx.deps.status_callback(f"✅ Decipherer analyzed: {truncate_for_log(result.output)[:200]}...")
        
        # Update tool log with result
        await ctx.deps.logging_service.update_tool_log(
            log_id=tool_log_id,
            output_result=truncate_for_log(result.output)
        )
        
        return result.output

@master_agent.tool
async def call_reporter(ctx: RunContext[MasterDeps], raw_findings: str) -> str:
    """Send data to the Reporting Officer to format."""
    ctx.deps.status_callback("📝 Reporter is drafting the final document...")
    
    # Log the tool call
    async with ctx.deps.logging_service.log_tool_execution(
        tool_name="call_reporter",
        tool_type="agent_call",
        input_arguments={"raw_findings": raw_findings[:500] + "..."}  # Truncate for logging
    ) as tool_log_id:
        # Log the agent execution
        prompt = f"Format this data: {raw_findings}"
        async with ctx.deps.logging_service.log_agent_execution(
            agent_name="writer_agent",
            agent_role="Reporter",
            input_prompt=truncate_for_log(prompt),
            model_name=writer_agent.model
        ) as agent_log_id:
            # Run the sub-agent
            result = await writer_agent.run(prompt)
            
            # Extract token usage
            usage = extract_usage_from_result(result)
            
            # Update agent log with output and usage
            await ctx.deps.logging_service.update_agent_log(
                log_id=agent_log_id,
                output_response=truncate_for_log(result.output),
                total_tokens=usage['total_tokens'],
                prompt_tokens=usage['prompt_tokens'],
                completion_tokens=usage['completion_tokens']
            )
            
            # Stream the sub-agent response
            ctx.deps.status_callback(f"✅ Reporter completed formatting")
        
        # Update tool log with result
        await ctx.deps.logging_service.update_tool_log(
            log_id=tool_log_id,
            output_result=truncate_for_log(result.output)
        )
        
        return result.output



# --- CLIENT WRAPPER ---
class MultiAgentClient:
    def __init__(self, sse_url="http://localhost:8000/mcp"):
        self.sse_url = sse_url

    async def run_audit(self, user_prompt: str, status_callback):
        # Connect to MCP via SSE
        try:
            async with sse_client(self.sse_url) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the MCP session
                    await session.initialize()
                    
                    # Initialize Deps with logging service
                    logging_service = create_logging_service()
                    deps = MasterDeps(session, status_callback, logging_service)
                    
                    # Log the master agent execution
                    async with logging_service.log_agent_execution(
                        agent_name="master_agent",
                        agent_role="Audit Lead",
                        input_prompt=user_prompt,
                        model_name=master_agent.model
                    ) as master_log_id:
                        # Run Master Agent using the proper node-by-node streaming API
                        response_text = ""
                        
                        # Import all event types
                        from pydantic_ai import (
                            FinalResultEvent,
                            FunctionToolCallEvent,
                            FunctionToolResultEvent,
                            PartDeltaEvent,
                            PartStartEvent,
                            TextPartDelta,
                            ThinkingPartDelta,
                            ToolCallPartDelta,
                        )
                        
                        async with master_agent.iter(user_prompt, deps=deps) as run:
                            async for node in run:
                                if master_agent.is_user_prompt_node(node):
                                    # User prompt node - the user has provided input
                                    status_callback(f"📝 User prompt received: {node.user_prompt[:100]}...")
                                
                                elif master_agent.is_model_request_node(node):
                                    # Model request node - stream tokens from the model's request
                                    status_callback("🤖 Master agent is thinking...")
                                    async with node.stream(run.ctx) as request_stream:
                                        final_result_found = False
                                        is_tool_call_result = False
                                        
                                        async for event in request_stream:
                                            if isinstance(event, PartDeltaEvent):
                                                # Streaming partial content
                                                if isinstance(event.delta, ThinkingPartDelta):
                                                    # Thinking/reasoning delta
                                                    status_callback(f"💭 Thinking: {event.delta.content_delta[:50]}...")
                                            
                                            elif isinstance(event, FinalResultEvent):
                                                final_result_found = True
                                                break
                                        
                                        if final_result_found and not is_tool_call_result:
                                            # Reset response_text to only capture the final answer
                                            response_text = ""
                                            yield "\n\n"
                                            async for output in request_stream.stream_text():
                                                # Stream the full output as it comes
                                                new_text = output[len(response_text):]
                                                if new_text:
                                                    response_text = output
                                                    yield new_text
                                
                                elif master_agent.is_call_tools_node(node):
                                    # Handle response node - model returned data, potentially calls tools
                                    async with node.stream(run.ctx) as handle_stream:
                                        async for event in handle_stream:
                                            if isinstance(event, FunctionToolCallEvent):
                                                # The LLM is calling a tool
                                                #status_callback(
                                                #    f"🔧 Calling tool: {event.part.tool_name} "
                                                #    f"(call_id: {event.part.tool_call_id[:8]}...)"
                                                #)
                                                pass
                                            elif isinstance(event, FunctionToolResultEvent):
                                                # Tool call completed and returned a result
                                                #result_preview = str(event.result.content)[:100]
                                                #status_callback(
                                                #    f"✅ Tool {event.tool_call_id[:8]}... returned: {result_preview}..."
                                                #)
                                                pass
                                
                                
                                elif master_agent.is_end_node(node):
                                    # Run is complete
                                    assert run.result is not None
                                    
                                    # Display emphasized final answer
                                    status_callback("="*60)
                                    status_callback("🎯 ✨ FINAL ANSWER ✨ 🎯")
                                    status_callback("="*60)
                                    status_callback(f"{response_text}")
                                    status_callback("="*60)
                                    status_callback("🎉 Master agent execution complete")
                                    break
                        
                        # Extract token usage from result
                        usage = extract_usage_from_result(run.result)
                        
                        # Update master agent log with final output and usage
                        await logging_service.update_agent_log(
                            log_id=master_log_id,
                            output_response=truncate_for_log(response_text),
                            total_tokens=usage['total_tokens'],
                            prompt_tokens=usage['prompt_tokens'],
                            completion_tokens=usage['completion_tokens']
                        )
        except httpx.HTTPStatusError as e:
            status_callback(f"❌ MCP Server Error ({e.response.status_code}): {e.response.text if e.response else 'Connection failed'}")
            status_callback(f"💡 Tip: Make sure MCP server is running with 'sse' transport")
            raise
        except Exception as e:
            status_callback(f"❌ Connection Error: {str(e)}")
            raise