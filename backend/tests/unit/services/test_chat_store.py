import pytest
from unittest.mock import patch
from uuid import uuid4
from datetime import datetime

from src.services.chat_store import ChatStore
from src.models.chat import Chat, Message


@pytest.mark.unit
class TestChatStore:
    """Tests for ChatStore service."""
    
    @pytest.fixture
    def chat_store(self):
        return ChatStore()
    
    def test_create_chat(self, chat_store, sync_session):
        """Test creating a chat."""
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            chat = chat_store.create_chat(name="Test Chat", user_id=str(uuid4()))
            
            assert chat["name"] == "Test Chat"
            assert chat["turns"] == 0
            
            from uuid import UUID
            chat_id = UUID(chat["id"])
            db_chat = sync_session.query(Chat).filter(Chat.id == chat_id).first()
            assert db_chat is not None
            assert db_chat.name == "Test Chat"

    def test_list_chats(self, chat_store, sync_session):
        """Test listing chats."""
        user_id = uuid4()
        
        chat1 = Chat(id=uuid4(), user_id=user_id, name="Chat 1", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        chat2 = Chat(id=uuid4(), user_id=user_id, name="Chat 2", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add_all([chat1, chat2])
        sync_session.commit()
        
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            chats = chat_store.list_chats(user_id=str(user_id))
            
            assert len(chats) == 2
            names = [c["name"] for c in chats]
            assert "Chat 1" in names
            assert "Chat 2" in names

    def test_rename_chat(self, chat_store, sync_session):
        """Test renaming a chat."""
        user_id = uuid4()
        chat = Chat(id=uuid4(), user_id=user_id, name="Old Name", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()
        
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            result = chat_store.rename_chat(chat_id=chat.id, name="New Name", user_id=str(user_id))
            
            assert result is True
            sync_session.refresh(chat)
            assert chat.name == "New Name"

    def test_delete_chat(self, chat_store, sync_session):
        """Test deleting a chat."""
        user_id = uuid4()
        chat = Chat(id=uuid4(), user_id=user_id, name="To Delete", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()
        
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            result = chat_store.delete_chat(chat_id=chat.id, user_id=str(user_id))
            
            assert result is True
            db_chat = sync_session.query(Chat).filter(Chat.id == chat.id).first()
            assert db_chat is None

    def test_add_message(self, chat_store, sync_session):
        """Test adding a message."""
        user_id = uuid4()
        chat = Chat(id=uuid4(), user_id=user_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()
        
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            msg = chat_store.add_message(
                chat_id=chat.id,
                role="user",
                content="Hello",
                user_id=str(user_id)
            )
            
            assert msg["content"] == "Hello"
            assert msg["role"] == "user"
            
            sync_session.refresh(chat)
            
            chats = chat_store.list_chats(user_id=str(user_id))
            assert chats[0]["turns"] == 1
            assert chats[0]["last_message_preview"] == "Hello"

    def test_list_messages(self, chat_store, sync_session):
        """Test listing messages."""
        user_id = uuid4()
        chat = Chat(id=uuid4(), user_id=user_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()
        
        msg1 = Message(id=uuid4(), chat_id=chat.id, role="user", content="Hi", created_at=datetime.utcnow())
        msg2 = Message(id=uuid4(), chat_id=chat.id, role="assistant", content="Hello", created_at=datetime.utcnow())
        sync_session.add_all([msg1, msg2])
        sync_session.commit()
        
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            msgs = chat_store.list_messages(chat_id=chat.id, user_id=str(user_id))
            
            assert len(msgs) == 2
            contents = [m["content"] for m in msgs]
            assert "Hi" in contents
            assert "Hello" in contents

    def test_get_chat(self, chat_store, sync_session):
        """Test getting a chat."""
        user_id = uuid4()
        chat = Chat(id=uuid4(), user_id=user_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()
        
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session
            
            result = chat_store.get_chat(chat_id=chat.id, user_id=str(user_id))
            
            assert result is not None
            assert result["id"] == str(chat.id)
            assert result["name"] == "Chat"

    def test_to_uuid_variants(self, chat_store):
        """_to_uuid should handle None, UUID, string UUID, and invalid values."""
        from uuid import UUID

        assert chat_store._to_uuid(None) is None

        original = uuid4()
        assert chat_store._to_uuid(original) == original

        as_str = str(uuid4())
        converted = chat_store._to_uuid(as_str)
        assert isinstance(converted, UUID)
        assert str(converted) == as_str

        assert chat_store._to_uuid("not-a-uuid") is None

    def test_rename_chat_not_found(self, chat_store, sync_session):
        """rename_chat should return False when chat does not exist."""
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            result = chat_store.rename_chat(chat_id=uuid4(), name="New", user_id=None)

        assert result is False

    def test_rename_chat_unauthorized(self, chat_store, sync_session):
        """rename_chat should return False when user_id does not match chat owner."""
        owner_id = uuid4()
        other_id = uuid4()
        chat = Chat(id=uuid4(), user_id=owner_id, name="Title", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()

        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            result = chat_store.rename_chat(chat_id=chat.id, name="New", user_id=str(other_id))

        assert result is False
        sync_session.refresh(chat)
        assert chat.name == "Title"

    def test_delete_chat_not_found(self, chat_store, sync_session):
        """delete_chat should return False when chat does not exist."""
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            result = chat_store.delete_chat(chat_id=uuid4(), user_id=None)

        assert result is False

    def test_delete_chat_unauthorized(self, chat_store, sync_session):
        """delete_chat should return False when user_id does not match chat owner."""
        owner_id = uuid4()
        other_id = uuid4()
        chat = Chat(id=uuid4(), user_id=owner_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()

        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            result = chat_store.delete_chat(chat_id=chat.id, user_id=str(other_id))

        assert result is False
        assert sync_session.query(Chat).filter(Chat.id == chat.id).one() is not None

    def test_add_message_chat_not_found(self, chat_store, sync_session):
        """add_message should raise when chat does not exist."""
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            with pytest.raises(ValueError):
                chat_store.add_message(
                    chat_id=uuid4(),
                    role="user",
                    content="Hello",
                    user_id=str(uuid4()),
                )

    def test_add_message_unauthorized(self, chat_store, sync_session):
        """add_message should raise when user_id does not match chat owner."""
        owner_id = uuid4()
        other_id = uuid4()
        chat = Chat(id=uuid4(), user_id=owner_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()

        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            with pytest.raises(ValueError):
                chat_store.add_message(
                    chat_id=chat.id,
                    role="user",
                    content="Hello",
                    user_id=str(other_id),
                )

    def test_list_messages_chat_not_found(self, chat_store, sync_session):
        """list_messages should raise when chat does not exist."""
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            with pytest.raises(ValueError):
                chat_store.list_messages(chat_id=uuid4(), user_id=str(uuid4()))

    def test_list_messages_unauthorized(self, chat_store, sync_session):
        """list_messages should raise when user_id does not match chat owner."""
        owner_id = uuid4()
        other_id = uuid4()
        chat = Chat(id=uuid4(), user_id=owner_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()

        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            with pytest.raises(ValueError):
                chat_store.list_messages(chat_id=chat.id, user_id=str(other_id))

    def test_get_chat_not_found(self, chat_store, sync_session):
        """get_chat should return None when chat is missing."""
        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            result = chat_store.get_chat(chat_id=uuid4(), user_id=str(uuid4()))

        assert result is None

    def test_get_chat_unauthorized(self, chat_store, sync_session):
        """get_chat should return None when user_id does not match chat owner."""
        owner_id = uuid4()
        other_id = uuid4()
        chat = Chat(id=uuid4(), user_id=owner_id, name="Chat", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        sync_session.add(chat)
        sync_session.commit()

        with patch("src.services.chat_store.get_sync_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = sync_session

            result = chat_store.get_chat(chat_id=chat.id, user_id=str(other_id))

        assert result is None
