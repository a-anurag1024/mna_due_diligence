"""
Logging service for tracking agent and tool executions.
Provides context managers and decorators for automatic logging to database.
"""
import time
import uuid
import json
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession

from ..db import AgentLog, ToolLog, AsyncSessionLocal


class LoggingContext:
    """Context manager for tracking nested agent/tool calls"""
    
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.current_agent_id: Optional[int] = None
        self.parent_agent_id: Optional[int] = None
    
    def set_current_agent(self, agent_id: int):
        """Set the current agent context"""
        self.current_agent_id = agent_id
    
    def push_agent(self, agent_id: int):
        """Push a new agent context (for nested calls)"""
        self.parent_agent_id = self.current_agent_id
        self.current_agent_id = agent_id
    
    def pop_agent(self):
        """Pop back to parent agent context"""
        self.current_agent_id = self.parent_agent_id
        self.parent_agent_id = None


class LoggingService:
    """Service for logging agent and tool executions"""
    
    def __init__(self):
        self.context = LoggingContext()
    
    @asynccontextmanager
    async def log_agent_execution(
        self,
        agent_name: str,
        input_prompt: str,
        agent_role: Optional[str] = None,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for logging agent execution.
        
        Usage:
            async with logging_service.log_agent_execution("master_agent", prompt) as log_id:
                # Execute agent
                result = await agent.run(prompt)
                yield result
        """
        async with AsyncSessionLocal() as session:
            # Create initial log entry
            agent_log = AgentLog(
                agent_name=agent_name,
                agent_role=agent_role,
                input_prompt=input_prompt,
                model_name=model_name,
                status="started",
                session_id=self.context.session_id,
                parent_agent_id=self.context.current_agent_id,
                meta_data=metadata,
            )
            
            session.add(agent_log)
            await session.commit()
            await session.refresh(agent_log)
            
            log_id = agent_log.id
            start_time = time.time()
            
            # Push this agent onto the context stack
            self.context.push_agent(log_id)
            
            try:
                # Yield control back to caller with log_id
                yield log_id
                
                # Success - update log entry
                latency_ms = (time.time() - start_time) * 1000
                agent_log.latency_ms = latency_ms
                agent_log.status = "completed"
                
                await session.commit()
                
            except Exception as e:
                # Error - log it
                latency_ms = (time.time() - start_time) * 1000
                agent_log.latency_ms = latency_ms
                agent_log.status = "error"
                agent_log.error_message = str(e)
                
                await session.commit()
                raise
            
            finally:
                # Pop agent from context
                self.context.pop_agent()
    
    async def update_agent_log(
        self,
        log_id: int,
        output_response: Optional[str] = None,
        total_tokens: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Update an existing agent log entry with results and metrics"""
        async with AsyncSessionLocal() as session:
            agent_log: AgentLog = await session.get(AgentLog, log_id)
            if agent_log:
                if output_response is not None:
                    agent_log.output_response = output_response
                if total_tokens is not None:
                    agent_log.total_tokens = total_tokens
                if prompt_tokens is not None:
                    agent_log.prompt_tokens = prompt_tokens
                if completion_tokens is not None:
                    agent_log.completion_tokens = completion_tokens
                if cost is not None:
                    agent_log.cost = cost
                if metadata is not None:
                    # Merge with existing metadata
                    existing_metadata = agent_log.meta_data or {}
                    existing_metadata.update(metadata)
                    agent_log.meta_data = existing_metadata
                
                await session.commit()
    
    @asynccontextmanager
    async def log_tool_execution(
        self,
        tool_name: str,
        input_arguments: Dict[str, Any],
        tool_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for logging tool execution.
        
        Usage:
            async with logging_service.log_tool_execution("search_vdr", {"query": "..."}) as log_id:
                # Execute tool
                result = await tool()
                yield result
        """
        async with AsyncSessionLocal() as session:
            # Create initial log entry
            tool_log = ToolLog(
                tool_name=tool_name,
                tool_type=tool_type,
                input_arguments=input_arguments,
                status="started",
                agent_log_id=self.context.current_agent_id,
                meta_data=metadata,
            )
            
            session.add(tool_log)
            await session.commit()
            await session.refresh(tool_log)
            
            log_id = tool_log.id
            start_time = time.time()
            
            try:
                # Yield control back to caller
                yield log_id
                
                # Success - update log entry
                latency_ms = (time.time() - start_time) * 1000
                tool_log.latency_ms = latency_ms
                tool_log.status = "completed"
                
                await session.commit()
                
            except Exception as e:
                # Error - log it
                latency_ms = (time.time() - start_time) * 1000
                tool_log.latency_ms = latency_ms
                tool_log.status = "error"
                tool_log.error_message = str(e)
                
                await session.commit()
                raise
    
    async def update_tool_log(
        self,
        log_id: int,
        output_result: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Update an existing tool log entry with results"""
        async with AsyncSessionLocal() as session:
            tool_log: ToolLog = await session.get(ToolLog, log_id)
            if tool_log:
                if output_result is not None:
                    tool_log.output_result = output_result
                if metadata is not None:
                    # Merge with existing metadata
                    existing_metadata = tool_log.meta_data or {}
                    existing_metadata.update(metadata)
                    tool_log.meta_data = existing_metadata
                
                await session.commit()


def create_logging_service() -> LoggingService:
    """Factory function to create a new logging service"""
    return LoggingService()


# Helper function to truncate long strings for logging
def truncate_for_log(text: str, max_length: int = 5000) -> str:
    """Truncate text for logging while keeping it readable"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"... [truncated, total length: {len(text)}]"
