import json
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from mna_due_diligence.db import LLMLog, Base
from config import settings


class LLMLogger:
    _table_initialized = False
    _init_lock = asyncio.Lock()
    
    def __init__(self):
        self.db_engine = create_async_engine(settings.DB_URL, echo=False)
        self.SessionLocal = async_sessionmaker(self.db_engine, expire_on_commit=False)
    
    async def _ensure_table_exists(self):
        """Ensure the llm_logs table exists. Only runs once per application lifecycle."""
        if not LLMLogger._table_initialized:
            async with LLMLogger._init_lock:
                # Double-check after acquiring lock
                if not LLMLogger._table_initialized:
                    async with self.db_engine.begin() as conn:
                        await conn.run_sync(Base.metadata.create_all)
                    LLMLogger._table_initialized = True

    def log(self, record: Dict[str, Any]):
        """
        Synchronous wrapper for logging. Creates an event loop if needed.
        Use this for backward compatibility with synchronous code.
        """
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an async context, schedule the coroutine
            asyncio.create_task(self._async_log(record))
        except RuntimeError:
            # No running loop, create a new one for this operation
            asyncio.run(self._log_and_cleanup(record))
    
    async def _log_and_cleanup(self, record: Dict[str, Any]):
        """Log and ensure proper cleanup for sync contexts."""
        try:
            await self._async_log(record)
        finally:
            # Close the engine to prevent connection cleanup warnings
            await self.db_engine.dispose()
    
    async def log_async(self, record: Dict[str, Any]):
        """
        Async method for logging. Use this when calling from async code.
        """
        await self._async_log(record)
    
    async def _async_log(self, record: Dict[str, Any]):
        """Internal async implementation of logging."""
        # Ensure table exists before logging
        await self._ensure_table_exists()
        
        async with self.SessionLocal() as session:
            # Extract common fields from the record
            log_entry = LLMLog(
                model=record.get("model"),
                operation=record.get("operation") or record.get("interaction_type"),
                prompt=self._extract_prompt(record),
                response=self._extract_response(record),
                tokens_used=self._extract_tokens(record),
                latency_ms=record.get("latency_ms"),
                cost=record.get("cost"),
                status=record.get("status"),
                error=record.get("error"),
                additional_metadata=self._extract_metadata(record)
            )
            
            session.add(log_entry)
            await session.commit()
    
    def _extract_prompt(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract prompt from various record formats."""
        if "prompt" in record:
            return record["prompt"]
        if "input" in record:
            input_data = record["input"]
            if isinstance(input_data, dict):
                return json.dumps(input_data)
            return str(input_data)
        return None
    
    def _extract_response(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract response from various record formats."""
        if "response" in record:
            return record["response"]
        if "output" in record:
            output_data = record["output"]
            if isinstance(output_data, dict):
                return json.dumps(output_data)
            return str(output_data)
        return None
    
    def _extract_tokens(self, record: Dict[str, Any]) -> Optional[int]:
        """Extract token count from various record formats."""
        if "tokens_used" in record:
            return record["tokens_used"]
        if "usage" in record and isinstance(record["usage"], dict):
            return record["usage"].get("total_tokens")
        return None
    
    def _extract_metadata(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract any additional fields not covered by the main columns."""
        known_fields = {
            "model", "operation", "interaction_type", "prompt", "response", 
            "input", "output", "tokens_used", "latency_ms", "cost", 
            "status", "error", "usage", "provider"
        }
        
        metadata = {k: v for k, v in record.items() if k not in known_fields}
        
        # Include provider if present
        if "provider" in record:
            metadata["provider"] = record["provider"]
        
        return metadata if metadata else None
    
    async def close(self):
        """Close the database engine."""
        await self.db_engine.dispose()


