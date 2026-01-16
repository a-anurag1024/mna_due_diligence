from langchain.tools import tool
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import Optional

from mna_due_diligence.db import Contract, FileState
from mna_due_diligence.index.config import get_config
from mna_due_diligence.index.processing import BGEEmbedder

# Initialize infrastructure (all synchronous)
config = get_config()
embedder = BGEEmbedder(model_name=config.EMBEDDING_MODEL, device="cpu")

# Synchronous database engine - convert async URL to sync
db_url = config.DB_URL
# Replace async drivers with sync equivalents
if '+asyncpg' in db_url:
    db_url = db_url.replace('+asyncpg', '')  # postgresql+asyncpg -> postgresql
elif '+aiosqlite' in db_url:
    db_url = db_url.replace('+aiosqlite', '')  # sqlite+aiosqlite -> sqlite
elif '+aiomysql' in db_url:
    db_url = db_url.replace('+aiomysql', '+pymysql')  # mysql+aiomysql -> mysql+pymysql
elif '+asyncmy' in db_url:
    db_url = db_url.replace('+asyncmy', '+pymysql')  # mysql+asyncmy -> mysql+pymysql
    
db_engine = create_engine(db_url, echo=False, future=True)
SessionLocal = sessionmaker(db_engine, expire_on_commit=False)

# Synchronous Qdrant client
qdrant = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)


# --- LangChain Tools ---

@tool
def filter_contracts(contract_type: Optional[str] = None, party_name: Optional[str] = None) -> str:
    """
    Filter contracts using SQL metadata (Type, Party, Date).
    
    Args:
        contract_type: Type of contract to filter (e.g., "NDA", "Sales Agreement", "Service Agreement")
        party_name: Name of a party involved in the contract (searches both party_a and party_b)
    
    Returns:
        List of matching contracts with filename and party information
    """
    try:
        with SessionLocal() as session:
            stmt = select(Contract.filename, Contract.party_a, Contract.party_b, Contract.effective_date)
            
            if contract_type:
                stmt = stmt.where(Contract.contract_type == contract_type)
            if party_name:
                stmt = stmt.where(
                    (Contract.party_a.ilike(f"%{party_name}%")) | 
                    (Contract.party_b.ilike(f"%{party_name}%"))
                )
            
            result = session.execute(stmt)
            rows = result.all()
            
            if not rows:
                return "No matches found."
            return "\n".join([f"- filename: \"{r.filename}\" ({r.party_a} vs {r.party_b})" for r in rows])
    except Exception as e:
        return f"Error filtering contracts: {str(e)}"


@tool
def filter_contracts_advanced(sql_query: str) -> str:
    """
    Filter contracts using a custom SQL WHERE clause for advanced queries.
    
    Args:
        sql_query: Custom SQL WHERE clause (e.g., 'effective_date > "2023-01-01" AND contract_type = "NDA"')
    
    Returns:
        List of matching contracts with detailed information
    
    Example:
        sql_query = 'effective_date > "2020-01-01" AND contract_type = "NDA"'
    """
    try:
        with SessionLocal() as session:
            stmt = select(
                Contract.filename, 
                Contract.party_a, 
                Contract.party_b, 
                Contract.effective_date, 
                Contract.contract_type
            )
            stmt = stmt.where(text(sql_query))
            
            result = session.execute(stmt)
            rows = result.all()
            
            if not rows:
                return "No matches found."
            
            return "\n".join([
                f"- {r.filename} | Type: {r.contract_type} | {r.party_a} ↔ {r.party_b} | Date: {r.effective_date}"
                for r in rows
            ])
    except Exception as e:
        return f"Error with advanced filter: {str(e)}"


@tool
def search_clauses(query: str, filename: Optional[str] = None) -> str:
    """
    Perform semantic search for clauses or concepts in contracts using vector embeddings.
    
    Args:
        query: The search query or concept to look for (e.g., "termination clause", "liability cap", "intellectual property")
        filename: Optional filename to restrict search to a specific contract document
    
    Returns:
        Top 5 most relevant contract clauses matching the query with their source documents
    """
    try:
        # Embed the query
        query_vec = embedder.embed([query])[0]
        
        # Build filter if filename provided
        q_filter = None
        if filename:
            q_filter = Filter(must=[FieldCondition(key="filename", match=MatchValue(value=filename))])
        
        # Search in vector database (synchronous)
        results = qdrant.query_points(
            collection_name=config.COLLECTION_NAME,
            query=query_vec,
            query_filter=q_filter,
            limit=5
        ).points
        
        if not results:
            return "No matching clauses found."
        
        return "\n".join([
            f"--- Found in {r.payload['filename']} ---\n{r.payload['enriched_text']}\n" 
            for r in results
        ])
    except Exception as e:
        return f"Error searching clauses: {str(e)}"


@tool
def read_file(filename: str) -> str:
    """
    Read the full text content of a specified contract document.
    
    Args:
        filename: Name of the contract file to read
    
    Returns:
        The full text content of the document (truncated to 3000 characters to manage token limits)
    """
    try:
        with SessionLocal() as session:
            stmt = select(FileState.markdown).where(FileState.filename == filename)
            result = session.execute(stmt)
            row = result.scalar_one_or_none()
            
            if not row:
                return "File not found."
            
            return row[:3000]  # Limit tokens
    except Exception as e:
        return f"Error reading file: {str(e)}"


# Export tools list for easy import
vdr_tools = [
    filter_contracts,
    filter_contracts_advanced,
    search_clauses,
    read_file
]
