
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mcp.client import sse
from typing import Optional
import httpx
import os
from mcp import ClientSession
from mcp.client.sse import sse_client

app = FastAPI()
app = FastAPI(title="MCP HTTP Gateway")

MCP_URL = os.environ.get("MCP_SSE_URL", "http://localhost:8000/sse")
MCP_SSE_URL = "http://localhost:8000/sse"


async def get_mcp_session() -> ClientSession:
    async with sse_client(url=MCP_SSE_URL) as (reader, writer):
        session = ClientSession(reader, writer)
        await session.initialize()
        return session



class FilterContractsRequest(BaseModel):
    contract_type: Optional[str] = None
    party_name: Optional[str] = None


class FilterContractsAdvancedRequest(BaseModel):
    sql_query: str


class SearchClausesRequest(BaseModel):
    query: str
    filename: Optional[str] = None


class ReadFileRequest(BaseModel):
    filename: str


@app.post("/filter_contracts")
async def filter_contracts(request: FilterContractsRequest):
    """Filter contracts using SQL metadata"""
    # Direct call to your existing backend logic
    # Replace this with your actual implementation
    try:
        mcp_client = await get_mcp_session()
        result = await mcp_client.call_tool(
            "filter_contracts",
            arguments={"contract_type": request.contract_type, "party_name": request.party_name}
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@app.post("/filter_contracts_advanced")
async def filter_contracts_advanced(request: FilterContractsAdvancedRequest):
    """Filter contracts using SQL metadata"""
    # Direct call to your existing backend logic
    # Replace this with your actual implementation
    try:
        mcp_client = await get_mcp_session()
        result = await mcp_client.call_tool(
            "filter_contracts_advanced",
            arguments={"sql_query": request.sql_query}
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_clauses")
async def search_clauses(request: SearchClausesRequest):
    """Semantic search for clauses"""
    try:
        mcp_client = await get_mcp_session()
        result = await mcp_client.call_tool(
            "search_clauses",
            arguments={"query": request.query, "filename": request.filename}
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/read_file")
async def read_file(request: ReadFileRequest):
    """Read full document text"""
    try:
        mcp_client = await get_mcp_session()
        result = await mcp_client.call_tool(
            "read_file",
            arguments={"filename": request.filename}
        )
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
