from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class AgentLog(Base):
    """Log entry for agent executions"""
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Agent identification
    agent_name = Column(String(128), nullable=False, index=True)
    agent_role = Column(String(128), nullable=True)  # e.g., "Master", "RAG Scout", "Analyst"
    
    # Execution hierarchy (for nested agents)
    parent_agent_id = Column(Integer, ForeignKey('agent_logs.id'), nullable=True, index=True)
    session_id = Column(String(128), nullable=True, index=True)  # Group related agent calls
    
    # Input/Output
    input_prompt = Column(Text, nullable=True)
    output_response = Column(Text, nullable=True)
    
    # Model & Performance
    model_name = Column(String(128), nullable=True)
    total_tokens = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    
    # Status tracking
    status = Column(String(64), nullable=False, index=True)  # "started", "completed", "error"
    error_message = Column(Text, nullable=True)
    
    # Additional metadata
    meta_data = Column(JSON, nullable=True)
    
    # Relationships
    children = relationship("AgentLog", backref="parent", remote_side=[id])
    tool_calls = relationship("ToolLog", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentLog(id={self.id}, agent={self.agent_name}, status={self.status}, timestamp={self.timestamp})>"


class ToolLog(Base):
    """Log entry for tool executions"""
    __tablename__ = "tool_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Tool identification
    tool_name = Column(String(128), nullable=False, index=True)
    tool_type = Column(String(64), nullable=True)  # e.g., "mcp", "agent_call", "database"
    
    # Relationship to agent
    agent_log_id = Column(Integer, ForeignKey('agent_logs.id'), nullable=True, index=True)
    agent = relationship("AgentLog", back_populates="tool_calls")
    
    # Input/Output
    input_arguments = Column(JSON, nullable=True)
    output_result = Column(Text, nullable=True)
    
    # Performance
    latency_ms = Column(Float, nullable=True)
    
    # Status tracking
    status = Column(String(64), nullable=False, index=True)  # "started", "completed", "error"
    error_message = Column(Text, nullable=True)
    
    # Additional metadata
    meta_data = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<ToolLog(id={self.id}, tool={self.tool_name}, status={self.status}, timestamp={self.timestamp})>"
