import os
import asyncio
from mcp.server.fastmcp import FastMCP
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from mna_due_diligence.db import Contract, FileState
from mna_due_diligence.index.config import get_config
from mna_due_diligence.index.processing import BGEEmbedder 

# Initialize FastMCP
mcp = FastMCP("MNA_DealScout_VDR")

# Load Config
config = get_config()

# --- INFRASTRUCTURE SETUP ---

embedder = BGEEmbedder(model_name=config.EMBEDDING_MODEL, device="cpu")

db_engine = create_async_engine(config.DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)
qdrant = AsyncQdrantClient(url=config.QDRANT_URL,
                           api_key=config.QDRANT_API_KEY)

# --- TOOLS ---

@mcp.tool()
async def filter_contracts(contract_type: str = None, party_name: str = None) -> str:
    """Filter contracts using SQL metadata (Type, Party, Date)."""
    async with AsyncSessionLocal() as session:
        stmt = select(Contract.filename, Contract.party_a, Contract.party_b, Contract.effective_date)
        
        if contract_type:
            stmt = stmt.where(Contract.contract_type == contract_type)
        if party_name:
            stmt = stmt.where((Contract.party_a.ilike(f"%{party_name}%")) | (Contract.party_b.ilike(f"%{party_name}%")))
            
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows: return "No matches found."
        return "\n".join([f"- {r.filename} ({r.party_a} vs {r.party_b})" for r in rows])
    
@mcp.tool()
async def filter_contracts_advanced(sql_query: str) -> str:
    """Filter contracts using a custom SQL WHERE clause (e.g., 'effective_date > \"2023-01-01\" AND contract_type = \"NDA\"')."""
    async with AsyncSessionLocal() as session:
        try:
            # Build base query
            stmt = select(Contract.filename, Contract.party_a, Contract.party_b, 
                            Contract.effective_date, Contract.contract_type)
            
            # Append custom WHERE clause
            stmt = stmt.where(sql_query)
            
            result = await session.execute(stmt)
            rows = result.all()
            
            if not rows:
                return "No matches found."
            
            return "\n".join([
                f"- {r.filename} | Type: {r.contract_type} | {r.party_a} ↔ {r.party_b} | Date: {r.effective_date}"
                for r in rows
            ])
        except Exception as e:
            return f"Error executing query: {str(e)}"

@mcp.tool()
async def search_clauses(query: str, filename: str = None) -> str:
    """Semantic search for clauses/concepts."""
    # 1. Embed query (CPU)
    query_vec = embedder.embed([query])[0] # Returns list of floats

    # 2. Filter
    q_filter = None
    if filename:
        q_filter = Filter(must=[FieldCondition(key="filename", match=MatchValue(value=filename))])

    # 3. Search using query_points for AsyncQdrantClient
    results = await qdrant.query_points(
        collection_name=config.COLLECTION_NAME,
        query=query_vec,
        query_filter=q_filter,
        limit=5
    )
    
    return "\n".join([f"--- Found in {r.payload['filename']} ---\n{r.payload['enriched_text']}\n" for r in results.points])

@mcp.tool()
async def read_file(filename: str) -> str:
    """Read raw file content from database."""
    async with AsyncSessionLocal() as session:
        stmt = select(FileState.markdown).where(FileState.filename == filename)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        
        if not row:
            return "File not found."
        
        return row[:3000]  # Limit tokens

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Use 'sse' transport for Server-Sent Events
    print("Starting MCP server with SSE transport...")
    mcp.run(transport="sse")