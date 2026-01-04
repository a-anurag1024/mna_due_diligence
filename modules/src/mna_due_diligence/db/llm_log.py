from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON
from sqlalchemy.sql import func

from .base import Base


class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Core fields - common to all log entries
    model = Column(String(128), nullable=True, index=True)
    operation = Column(String(128), nullable=True, index=True)
    
    # Request/Response data
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    
    # Metrics
    tokens_used = Column(Integer, nullable=True)
    latency_ms = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    
    # Status/Error tracking
    status = Column(String(64), nullable=True, index=True)
    error = Column(Text, nullable=True)
    
    # Additional metadata as JSON
    additional_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<LLMLog(id={self.id}, model={self.model}, operation={self.operation}, timestamp={self.timestamp})>"
