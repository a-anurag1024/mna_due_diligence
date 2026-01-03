
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
    markdown = Column(Text(length=16777215), nullable=True)  # MEDIUMTEXT in MySQL, ~16MB
    page_count = Column(String(50), nullable=True)
