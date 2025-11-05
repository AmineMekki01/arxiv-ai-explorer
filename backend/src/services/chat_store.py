from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4, UUID
from src.database import get_sync_session
from src.models.chat import Chat, Message

class ChatStore:
    def __init__(self):
        pass

    @staticmethod
    def _to_uuid(value: Optional[str | UUID]) -> Optional[UUID]:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except Exception:
            return None

    def create_chat(self, name: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        with get_sync_session() as db:
            chat = Chat(
                id=str(uuid4()),
                user_id=user_id,
                name=name,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                turns=0
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return self._chat_to_dict(chat)

    def list_chats(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_sync_session() as db:
            q = db.query(Chat)
            uid = self._to_uuid(user_id)
            if uid is not None:
                q = q.filter(Chat.user_id == uid)
            chats = q.order_by(Chat.updated_at.desc()).all()
            return [self._chat_to_dict(c) for c in chats]

    def rename_chat(self, chat_id: str, name: str, user_id: Optional[str] = None) -> bool:
        with get_sync_session() as db:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                return False
            uid = self._to_uuid(user_id)
            if uid is not None and chat.user_id != uid:
                return False
            chat.name = name
            chat.updated_at = datetime.utcnow()
            db.commit()
            return True

    def delete_chat(self, chat_id: str, user_id: Optional[str] = None) -> bool:
        with get_sync_session() as db:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                return False
            uid = self._to_uuid(user_id)
            if uid is not None and chat.user_id != uid:
                return False
            db.delete(chat)
            db.commit()
            return True

    def add_message(self, chat_id: str, role: str, content: str, user_id: Optional[str] = None, client_msg_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with get_sync_session() as db:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
            uid = self._to_uuid(user_id)
            if chat.user_id is None and uid is not None:
                chat.user_id = uid
                db.commit()
                db.refresh(chat)
            if uid is not None and chat.user_id != uid:
                raise ValueError("Unauthorized")
            msg = Message(
                id=str(uuid4()),
                chat_id=chat_id,
                user_id=uid,
                role=role,
                content=content,
                created_at=datetime.utcnow(),
                client_msg_id=client_msg_id,
                message_metadata=metadata or {}
            )
            db.add(msg)
            chat.turns += 1
            chat.updated_at = datetime.utcnow()
            chat.last_message_preview = (content or "")[:200]
            db.commit()
            db.refresh(msg)
            return self._message_to_dict(msg)

    def list_messages(self, chat_id: str, before: Optional[str] = None, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_sync_session() as db:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
            uid = self._to_uuid(user_id)
            if uid is not None and chat.user_id != uid:
                raise ValueError("Unauthorized")
            q = db.query(Message).filter(Message.chat_id == chat_id)
            if before:
                try:
                    before_dt = datetime.fromisoformat(before)
                    q = q.filter(Message.created_at < before_dt)
                except Exception:
                    q = q.filter(Message.id < before)
            msgs = q.order_by(Message.created_at.desc()).limit(limit).all()
            return [self._message_to_dict(m) for m in msgs]

    def get_chat(self, chat_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with get_sync_session() as db:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                return None
            uid = self._to_uuid(user_id)
            if chat.user_id is None and uid is not None:
                chat.user_id = uid
                db.commit()
                db.refresh(chat)
            if uid is not None and chat.user_id != uid:
                return None
            return self._chat_to_dict(chat)

    @staticmethod
    def _chat_to_dict(chat: Chat) -> Dict[str, Any]:
        return {
            "id": str(chat.id),
            "user_id": chat.user_id,
            "name": chat.name,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
            "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            "last_message_preview": chat.last_message_preview,
            "turns": chat.turns
        }

    @staticmethod
    def _message_to_dict(msg: Message) -> Dict[str, Any]:
        message_metadata = msg.message_metadata or {}
        return {
            "id": str(msg.id),
            "chat_id": str(msg.chat_id),
            "user_id": msg.user_id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "client_msg_id": msg.client_msg_id,
            "sources": message_metadata.get("sources", []),
            "graph_insights": message_metadata.get("graph_insights", {})
        }
