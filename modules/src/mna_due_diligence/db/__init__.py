from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

from .base import Base
from .file_state import FileState, ProcessingStatus
from .contract_metadata import Contract
from .llm_log import LLMLog
from .agent_log import AgentLog, ToolLog


# Async Engine
engine = create_async_engine(settings.DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)