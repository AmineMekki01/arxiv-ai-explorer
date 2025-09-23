from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.agents.base_agent import BaseAgent

router = APIRouter(prefix="/assistant", tags=["assistant"])

retrieval_agent = BaseAgent()

@router.get("")
async def query_agent(
    q: str = Query(..., description="User query"),
    chat_id: str = Query(..., description="Chat ID"),
):
    """Unified search endpoint. Returns results depending on selected mode."""
    try:
        result = await retrieval_agent.process_query(q, chat_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
