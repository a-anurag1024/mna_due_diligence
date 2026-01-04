# database.py update
from sqlalchemy import Column, String, Date, Float, Text, Integer, DateTime
from sqlalchemy.sql import func
from .base import Base


class Contract(Base):
    __tablename__ = "contract_metadata"
    
    # Primary Key
    filename = Column(String(255), primary_key=True)
    
    # Metadata Fields (Extracted by LLM)
    title = Column(String(255), nullable=True)
    contract_type = Column(String(50), nullable=True)
    party_a = Column(String(255), nullable=True)
    party_b = Column(String(255), nullable=True)
    effective_date = Column(Date, nullable=True)
    expiration_date = Column(String(50), nullable=True) # String because "Perpetual" is valid
    governing_law = Column(String(100), nullable=True)