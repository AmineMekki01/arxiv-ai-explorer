import asyncio
from fastapi import APIRouter, HTTPException, Query, Depends, status
from pydantic import BaseModel, Field
from src.services.chat_store import ChatStore
from src.agents.base_agent import retrieval_agent
from src.core import logger
from src.routes.auth import require_auth
from src.models.user import User

router = APIRouter(prefix="/chats", tags=["chats"])
chat_store = ChatStore()

class CreateChatRequest(BaseModel):
    name: str | None = Field(default=None, description="Optional chat name")

class RenameChatRequest(BaseModel):
    name: str = Field(..., description="New chat name")

class MessageRequest(BaseModel):
    role: str = Field(..., description="Message role: user|assistant|system")
    content: str = Field(..., description="Message content")
    client_msg_id: str | None = Field(default=None, description="Client-side id for idempotency")

@router.get("")
async def list_chats(current_user: User = Depends(require_auth)):
    try:
        items = chat_store.list_chats(user_id=str(current_user.id))
        return {"status": "success", "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list chats: {e}")

@router.post("")
async def create_chat(request: CreateChatRequest, current_user: User = Depends(require_auth)):
    try:
        chat = chat_store.create_chat(name=request.name, user_id=str(current_user.id))
        return {"status": "success", "chat": chat}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat: {e}")

@router.post("/{chat_id}/rename")
async def rename_chat(chat_id: str, request: RenameChatRequest, current_user: User = Depends(require_auth)):
    try:
        ok = chat_store.rename_chat(chat_id, request.name, user_id=str(current_user.id))
        if not ok:
            raise HTTPException(status_code=404, detail="Chat not found")
        return {"status": "success", "chat_id": chat_id, "name": request.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename chat: {e}")

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, current_user: User = Depends(require_auth)):
    try:
        ok = chat_store.delete_chat(chat_id, user_id=str(current_user.id))
        if not ok:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        await retrieval_agent.delete_chat(chat_id)
        
        return {"status": "success", "chat_id": chat_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat: {e}")

@router.get("/{chat_id}/messages")
async def get_messages(chat_id: str, before: str | None = None, limit: int = 50, current_user: User = Depends(require_auth)):
    try:
        msgs = chat_store.list_messages(chat_id, before=before, limit=limit, user_id=str(current_user.id))
        return {"status": "success", "messages": msgs}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load messages: {e}")

@router.post("/{chat_id}/messages")
async def send_message(chat_id: str, request: MessageRequest, current_user: User = Depends(require_auth)):
    try:
        chat = chat_store.get_chat(chat_id, user_id=str(current_user.id))
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        if request.client_msg_id:
            existing = chat_store.list_messages(chat_id, limit=200, user_id=str(current_user.id))
            if any(m.get("client_msg_id") == request.client_msg_id for m in existing):
                for m in existing:
                    if m.get("client_msg_id") == request.client_msg_id and m["role"] == "assistant":
                        return {"status": "success", "message": m, "sources": [], "graph_insights": {}}
        
        chat_store.add_message(chat_id, request.role, request.content, user_id=str(current_user.id), client_msg_id=request.client_msg_id)
        result = await asyncio.wait_for(
            retrieval_agent.process_query(request.content, chat_id, "research"),
            timeout=90.0
        )
        
        if isinstance(result, dict):
            assistant_content = result.get("response", result.get("final_output", ""))
            sources = result.get("sources", [])
            graph_insights = result.get("graph_insights", {})
        else:
            assistant_content = str(result)
            sources = []
            graph_insights = {}
        
        metadata = {
            "sources": sources,
            "graph_insights": graph_insights
        }
        assistant_msg = chat_store.add_message(chat_id, "assistant", assistant_content, user_id=str(current_user.id), metadata=metadata)
        
        return {
            "status": "success", 
            "message": assistant_msg, 
            "sources": sources, 
            "graph_insights": graph_insights
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Query processing timed out")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")
