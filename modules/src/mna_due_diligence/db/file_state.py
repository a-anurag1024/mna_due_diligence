
import enum
from mna_due_diligence.db.base import Base
from sqlalchemy import Column, String, Enum, DateTime, Text
from sqlalchemy.sql import func


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileState(Base):
    __tablename__ = "pipeline_state"
    
    filename = Column(String(255), primary_key=True)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # We can also store metadata here
    contract_type = Column(String(100), nullable=True)
    page_count = Column(String(50), nullable=True)
