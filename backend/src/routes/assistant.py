from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.agents.base_agent import BaseAgent
from src.core import logger

router = APIRouter(prefix="/assistant", tags=["assistant"])

logger.info("Initializing BaseAgent for assistant routes")
retrieval_agent = BaseAgent()
logger.info("BaseAgent initialized successfully")

@router.get("/test")
async def test_assistant():
    """Quick test endpoint to verify assistant is working."""
    return {
        "status": "Assistant is ready",
        "message": "This is a simple test response",
        "timestamp": "2024-01-01T00:00:00Z"
    }

class QueryRequest(BaseModel):
    """Request model for agent queries."""
    query: str = Field(..., description="User's question or request")
    chat_id: str = Field(..., description="Unique conversation identifier")
    conversation_type: str = Field(default="research", description="Type of conversation: research, quick, analysis, general")
    
class ContextStrategyRequest(BaseModel):
    """Request model for changing context strategy."""
    strategy: str = Field(..., description="New context strategy: trimming, summarization, hybrid")

@router.get("/session/{chat_id}")
async def get_session_info(chat_id: str):
    """Get detailed information about a conversation session."""
    logger.info(f"📊 Getting session info for chat_id: {chat_id}")
    try:
        session_info = await retrieval_agent.get_session_info(chat_id)
        logger.info(f"✅ Session info retrieved: {session_info.get('status', 'unknown')} - {session_info.get('total_items', 0)} items")
        return {
            "status": "success",
            "session_info": session_info
        }
    except Exception as e:
        logger.error(f"❌ Failed to get session info for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {e}")

@router.get("")
async def query_agent(
    q: str = Query(..., description="User query"),
    chat_id: str = Query(..., description="Chat ID"),
    conversation_type: str = Query(default="research", description="Type of conversation: research, quick, analysis, general"),
):
    """Process a user query with intelligent context management."""
    try:
        result = await asyncio.wait_for(
            retrieval_agent.process_query(q, chat_id, conversation_type),
            timeout=90.0
        )
        
        session_info = await retrieval_agent.get_session_info(chat_id)
        
        return {
            "final_output": result,
            "status": "success",
            "chat_id": chat_id,
            "conversation_type": conversation_type,
            "session_info": session_info
        }
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408, 
            detail="Query processing timed out. Please try a simpler query or try again later."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {e}")

@router.post("/query")
async def query_agent_post(request: QueryRequest):
    """Process a user query with intelligent context management (POST version)."""
    logger.info(f"📥 POST /query - chat_id: {request.chat_id}, type: {request.conversation_type}")
    logger.info(f"💬 Query: {request.query[:100]}{'...' if len(request.query) > 100 else ''}")
    
    try:
        result = await asyncio.wait_for(
            retrieval_agent.process_query(
                request.query, 
                request.chat_id, 
                request.conversation_type
            ),
            timeout=90.0
        )
        
        session_info = await retrieval_agent.get_session_info(request.chat_id)
        
        logger.info(f"✅ Query processed successfully for {request.chat_id}")
        logger.info(f"📊 Session: {session_info.get('user_turns', 0)} turns, strategy: {session_info.get('current_strategy', 'unknown')}")
        
        return {
            "final_output": result,
            "status": "success",
            "chat_id": request.chat_id,
            "conversation_type": request.conversation_type,
            "session_info": session_info
        }
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ Query timeout for chat_id: {request.chat_id}")
        raise HTTPException(
            status_code=408, 
            detail="Query processing timed out. Please try a simpler query or try again later."
        )
    except Exception as e:
        logger.error(f"❌ Query processing failed for {request.chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {e}")

@router.delete("/session/{chat_id}")
async def clear_session(chat_id: str):
    """Clear a conversation session and its history."""
    logger.info(f"🗑️ Clearing session: {chat_id}")
    try:
        success = await retrieval_agent.clear_session(chat_id)
        if success:
            logger.info(f"✅ Session {chat_id} cleared successfully")
        else:
            logger.warning(f"⚠️ Session {chat_id} not found")
        return {
            "status": "success" if success else "not_found",
            "message": f"Session {chat_id} cleared" if success else f"Session {chat_id} not found",
            "chat_id": chat_id
        }
    except Exception as e:
        logger.error(f"❌ Failed to clear session {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {e}")

@router.post("/session/{chat_id}/strategy")
async def switch_context_strategy(chat_id: str, request: ContextStrategyRequest):
    """Switch the context management strategy for a session."""
    logger.info(f"🔄 Switching strategy for {chat_id} to: {request.strategy}")
    try:
        success = await retrieval_agent.switch_context_strategy(chat_id, request.strategy)
        
        if success:
            session_info = await retrieval_agent.get_session_info(chat_id)
            logger.info(f"✅ Strategy switched to {request.strategy} for {chat_id}")
            return {
                "status": "success",
                "message": f"Switched session {chat_id} to strategy: {request.strategy}",
                "chat_id": chat_id,
                "new_strategy": request.strategy,
                "session_info": session_info
            }
        else:
            logger.warning(f"⚠️ Session {chat_id} not found for strategy switch")
            return {
                "status": "not_found",
                "message": f"Session {chat_id} not found",
                "chat_id": chat_id
            }
    except Exception as e:
        logger.error(f"❌ Failed to switch strategy for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch strategy: {e}")

@router.get("/recommendations/{conversation_type}")
async def get_strategy_recommendations(conversation_type: str):
    """Get context management strategy recommendations for a conversation type."""
    try:
        recommendations = retrieval_agent.get_strategy_recommendations(conversation_type)
        return {
            "status": "success",
            "conversation_type": conversation_type,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {e}")

@router.get("/strategies")
async def list_available_strategies():
    """List all available context management strategies and their descriptions."""
    strategies = {
        "trimming": {
            "description": "Keep only the last N user turns in memory",
            "pros": ["Deterministic & simple", "Zero added latency", "Fidelity for recent work"],
            "cons": ["Forgets long-range context abruptly", "User experience amnesia"],
            "best_for": "Independent tasks with non-overlapping context"
        },
        "summarization": {
            "description": "Compress older messages into structured summaries",
            "pros": ["Retains long-range memory compactly", "Smoother UX", "Cost-controlled scale"],
            "cons": ["Summarization loss & bias", "Latency & cost spikes", "Compounding errors"],
            "best_for": "Tasks needing context across the flow (planning, analysis)"
        },
        "hybrid": {
            "description": "Adaptive strategy that switches between trimming and summarization",
            "pros": ["Best of both worlds", "Adapts to conversation complexity", "Balanced efficiency"],
            "cons": ["More complex", "Strategy switching overhead"],
            "best_for": "General purpose conversations with varying complexity"
        }
    }
    
    return {
        "status": "success",
        "strategies": strategies
    }
