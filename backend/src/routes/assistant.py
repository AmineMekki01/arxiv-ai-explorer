from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.agents.base_agent import retrieval_agent
from src.core import logger
from src.routes.auth import require_auth
from src.models.user import User
from src.services.chat_store import ChatStore

router = APIRouter(prefix="/assistant", tags=["assistant"])
chat_store = ChatStore()

class QueryRequest(BaseModel):
    """Request model for agent queries."""
    query: str = Field(..., description="User's question or request")
    chat_id: str = Field(..., description="Unique conversation identifier")
    conversation_type: str = Field(default="research", description="Type of conversation: research, quick, analysis, general")
    
class ContextStrategyRequest(BaseModel):
    strategy: str = Field(..., description="New context strategy: trimming, summarization, hybrid")

@router.get("/session/{chat_id}")
async def get_session_info(chat_id: str, current_user: User = Depends(require_auth)):
    """Get detailed information about a conversation session."""
    logger.info(f"Getting session info for chat_id: {chat_id}")
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        session_info = await retrieval_agent.get_session_info(chat_id)
        logger.info(f"Session info retrieved: {session_info.get('status', 'unknown')} - {session_info.get('total_items', 0)} items")
        return {
            "status": "success",
            "session_info": session_info
        }
    except Exception as e:
        logger.error(f"Failed to get session info for {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {e}")

@router.get("")
async def query_agent(
    q: str = Query(..., description="User query"),
    chat_id: str = Query(..., description="Chat ID"),
    conversation_type: str = Query(default="research", description="Type of conversation: research, quick, analysis, general"),
    current_user: User = Depends(require_auth)
):
    """Process a user query with intelligent context management."""
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        result = await asyncio.wait_for(
            retrieval_agent.process_query(q, chat_id, conversation_type),
            timeout=90.0
        )
        
        session_info = await retrieval_agent.get_session_info(chat_id)
        
        if isinstance(result, dict):
            return {
                "final_output": result.get("response", result.get("final_output", "")),
                "sources": result.get("sources", []),
                "graph_insights": result.get("graph_insights", {}),
                "tool_calls": result.get("tool_calls", []),
                "status": "success",
                "chat_id": chat_id,
                "conversation_type": conversation_type,
                "session_info": session_info
            }
        else:
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
async def query_agent_post(request: QueryRequest, current_user: User = Depends(require_auth)):
    """Process a user query with intelligent context management (POST version)."""
    logger.info(f"POST /query - chat_id: {request.chat_id}, type: {request.conversation_type}")
    logger.info(f"Query: {request.query[:100]}{'...' if len(request.query) > 100 else ''}")
    
    try:
        chat = chat_store.get_chat(request.chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        result = await asyncio.wait_for(
            retrieval_agent.process_query(
                request.query, 
                request.chat_id, 
                request.conversation_type
            ),
            timeout=90.0
        )
        
        session_info = await retrieval_agent.get_session_info(request.chat_id)
        
        logger.info(f"Query processed successfully for {request.chat_id}")
        logger.info(f"Session: {session_info.get('user_turns', 0)} turns, strategy: {session_info.get('current_strategy', 'unknown')}")
        
        if isinstance(result, dict):
            return {
                "final_output": result.get("response", result.get("final_output", "")),
                "sources": result.get("sources", []),
                "graph_insights": result.get("graph_insights", {}),
                "tool_calls": result.get("tool_calls", []),
                "status": "success",
                "chat_id": request.chat_id,
                "conversation_type": request.conversation_type,
                "session_info": session_info
            }
        else:
            return {
                "final_output": result,
                "status": "success",
                "chat_id": request.chat_id,
                "conversation_type": request.conversation_type,
                "session_info": session_info
            }
    except asyncio.TimeoutError:
        logger.warning(f"Query timeout for chat_id: {request.chat_id}")
        raise HTTPException(
            status_code=408, 
            detail="Query processing timed out. Please try a simpler query or try again later."
        )
    except Exception as e:
        logger.error(f"Query processing failed for {request.chat_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query processing failed: {e}")

@router.delete("/session/{chat_id}")
async def clear_session(chat_id: str):
    """Clear a conversation session and its history."""
    logger.info(f"Clearing session: {chat_id}")
    try:
        success = await retrieval_agent.clear_session(chat_id)
        if success:
            logger.info(f"Session {chat_id} cleared successfully")
        else:
            logger.warning(f"Session {chat_id} not found")
        return {
            "status": "success" if success else "not_found",
            "message": f"Session {chat_id} cleared" if success else f"Session {chat_id} not found",
            "chat_id": chat_id
        }
    except Exception as e:
        logger.error(f"Failed to clear session {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {e}")

@router.post("/session/{chat_id}/strategy")
async def switch_context_strategy(chat_id: str, request: ContextStrategyRequest):
    """Switch the context management strategy for a session."""
    logger.info(f"🔄 Switching strategy for {chat_id} to: {request.strategy}")
    try:
        success = await retrieval_agent.switch_context_strategy(chat_id, request.strategy)
        
        if success:
            session_info = await retrieval_agent.get_session_info(chat_id)
            logger.info(f"Strategy switched to {request.strategy} for {chat_id}")
            return {
                "status": "success",
                "message": f"Switched session {chat_id} to strategy: {request.strategy}",
                "chat_id": chat_id,
                "new_strategy": request.strategy,
                "session_info": session_info
            }
        else:
            logger.warning(f"Session {chat_id} not found for strategy switch")
            return {
                "status": "not_found",
                "message": f"Session {chat_id} not found",
                "chat_id": chat_id
            }
    except Exception as e:
        logger.error(f"Failed to switch strategy for {chat_id}: {e}")
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

class FocusPaperRequest(BaseModel):
    """Request model for focusing on a paper."""
    arxiv_id: str = Field(..., description="arXiv ID of the paper to focus on")
    title: str = Field(..., description="Title of the paper")

@router.post("/session/{chat_id}/focus")
async def add_focused_paper(chat_id: str, request: FocusPaperRequest, current_user: User = Depends(require_auth)):
    """Add a paper to the focus list for this session."""
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        retrieval_agent.add_focused_paper(chat_id, request.arxiv_id)
        focused_papers = retrieval_agent.get_focused_papers(chat_id)
        
        logger.info(f"Paper {request.arxiv_id} focused for chat {chat_id}")
        
        return {
            "status": "success",
            "message": f"Focused on paper: {request.title}",
            "arxiv_id": request.arxiv_id,
            "focused_count": len(focused_papers),
            "focused_papers": focused_papers
        }
    except Exception as e:
        logger.error(f"Failed to focus paper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to focus paper: {e}")

@router.delete("/session/{chat_id}/focus/{arxiv_id}")
async def remove_focused_paper(chat_id: str, arxiv_id: str, current_user: User = Depends(require_auth)):
    """Remove a paper from the focus list."""
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        retrieval_agent.remove_focused_paper(chat_id, arxiv_id)
        focused_papers = retrieval_agent.get_focused_papers(chat_id)
        
        logger.info(f"Paper {arxiv_id} unfocused for chat {chat_id}")
        
        return {
            "status": "success",
            "message": f"Unfocused paper: {arxiv_id}",
            "arxiv_id": arxiv_id,
            "focused_count": len(focused_papers),
            "focused_papers": focused_papers
        }
    except Exception as e:
        logger.error(f"Failed to unfocus paper: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unfocus paper: {e}")

@router.delete("/session/{chat_id}/focus")
async def clear_focused_papers(chat_id: str, current_user: User = Depends(require_auth)):
    """Clear all focused papers for this session."""
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        retrieval_agent.clear_focused_papers(chat_id)
        
        logger.info(f"🔄 Cleared all focused papers for chat {chat_id}")
        
        return {
            "status": "success",
            "message": "All focused papers cleared",
            "chat_id": chat_id,
            "focused_count": 0
        }
    except Exception as e:
        logger.error(f"Failed to clear focused papers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear focused papers: {e}")

@router.get("/session/{chat_id}/focus")
async def get_focused_papers(chat_id: str, current_user: User = Depends(require_auth)):
    """Get the list of currently focused papers for this session."""
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        focused_ids = retrieval_agent.get_focused_papers(chat_id)
        
        papers = []
        if focused_ids:
            from src.services.knowledge_graph import Neo4jClient
            try:
                with Neo4jClient() as client:
                    for arxiv_id in focused_ids:
                        result = client.execute_query("""
                            MATCH (p:Paper {arxiv_id: $id})
                            RETURN p.title as title, p.citation_count as citations
                        """, {"id": arxiv_id})
                        if result:
                            papers.append({
                                "arxiv_id": arxiv_id,
                                "title": result[0]["title"],
                                "citations": result[0].get("citations", 0)
                            })
            except Exception as e:
                logger.warning(f"Could not fetch paper details from graph: {e}")
                papers = [{"arxiv_id": arxiv_id, "title": arxiv_id} for arxiv_id in focused_ids]
        
        return {
            "status": "success",
            "chat_id": chat_id,
            "focused_papers": papers,
            "count": len(papers)
        }
    except Exception as e:
        logger.error(f"Failed to get focused papers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get focused papers: {e}")

@router.get("/papers/{arxiv_id}/detail")
async def get_paper_detail(arxiv_id: str):
    """Get detailed information about a specific paper."""
    try:
        from src.database import get_sync_session
        from src.models.paper import Paper
        from src.services.knowledge_graph import Neo4jClient
        
        logger.info(f"Fetching paper details for {arxiv_id}")
        
        paper_metadata = None
        try:
            with get_sync_session() as db:
                paper_metadata = db.query(Paper).filter(Paper.arxiv_id == arxiv_id).first()
                
                if paper_metadata:
                    logger.info(f"Paper found in PostgreSQL: {paper_metadata.title[:50]}...")
        except Exception as e:
            logger.warning(f"Could not query PostgreSQL: {e}")
        
        citation_count = 0
        is_seminal = False
        
        try:
            with Neo4jClient() as client:
                query = """
                MATCH (p:Paper {arxiv_id: $arxiv_id})
                OPTIONAL MATCH (cited:Paper)-[:CITES]->(p)
                WITH p, count(DISTINCT cited) as citation_count
                RETURN citation_count,
                       CASE WHEN citation_count > 100 THEN true ELSE false END as is_seminal
                """
                
                result = client.execute_query(query, {"arxiv_id": arxiv_id})
                
                if result and len(result) > 0:
                    citation_count = result[0].get("citation_count", 0)
                    is_seminal = result[0].get("is_seminal", False)
                    logger.info(f"Citation data from Neo4j: {citation_count} citations")
        except Exception as e:
            logger.warning(f"Could not get citation data from Neo4j: {e}")
        
        if paper_metadata:
            return {
                "status": "success",
                "data": {
                    "arxiv_id": paper_metadata.arxiv_id,
                    "title": paper_metadata.title,
                    "abstract": paper_metadata.abstract,
                    "authors": paper_metadata.authors if isinstance(paper_metadata.authors, list) else [],
                    "published_date": paper_metadata.published_date.isoformat() if paper_metadata.published_date else "",
                    "updated_date": paper_metadata.updated_date.isoformat() if paper_metadata.updated_date else None,
                    "primary_category": paper_metadata.primary_category,
                    "categories": paper_metadata.categories if isinstance(paper_metadata.categories, list) else [],
                    "citation_count": citation_count,
                    "is_seminal": is_seminal
                }
            }
        
        logger.error(f"Paper {arxiv_id} not found in database")
        raise HTTPException(status_code=404, detail=f"Paper {arxiv_id} not found in database")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get paper details: {str(e)}")
