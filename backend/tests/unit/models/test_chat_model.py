import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.models.chat import Chat, Message
from src.models.user import User


@pytest.mark.unit
class TestChatModel:
    """Tests for Chat model."""
    
    @pytest.mark.asyncio
    async def test_chat_creation(self, async_session):
        """Test creating a chat."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            username="testuser",
            hashed_password="hashed123",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        chat = Chat(
            id=uuid4(),
            user_id=user.id,
            name="Test Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        async_session.add(user)
        async_session.add(chat)
        await async_session.commit()
        
        assert chat.id is not None
        assert chat.user_id == user.id
        assert chat.name == "Test Chat"
        assert chat.created_at is not None
    
    @pytest.mark.asyncio
    async def test_chat_with_messages(self, async_session):
        """Test chat with messages relationship."""
        user = User(
            id=uuid4(),
            email="test2@example.com",
            username="testuser2",
            hashed_password="hashed123",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        chat = Chat(
            id=uuid4(),
            user_id=user.id,
            name="Chat with Messages",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        message = Message(
            id=uuid4(),
            chat_id=chat.id,
            role="user",
            content="Hello, this is a test message",
            created_at=datetime.now(timezone.utc),
            message_metadata={}
        )
        
        async_session.add(user)
        async_session.add(chat)
        async_session.add(message)
        await async_session.commit()
        
        assert message.chat_id == chat.id
        assert message.role == "user"
        assert message.content == "Hello, this is a test message"


@pytest.mark.unit
class TestMessageModel:
    """Tests for Message model."""
    
    @pytest.mark.asyncio
    async def test_message_creation(self, async_session):
        """Test creating a message."""
        user = User(
            id=uuid4(),
            email="test3@example.com",
            username="testuser3",
            hashed_password="hashed123",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        chat = Chat(
            id=uuid4(),
            user_id=user.id,
            name="Message Test Chat",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        message = Message(
            id=uuid4(),
            chat_id=chat.id,
            role="assistant",
            content="I am an AI assistant",
            created_at=datetime.now(timezone.utc),
            client_msg_id="client_123",
            message_metadata={"temperature": 0.7, "model": "gpt-4"}
        )
        
        async_session.add(user)
        async_session.add(chat)
        async_session.add(message)
        await async_session.commit()
        
        assert message.id is not None
        assert message.role == "assistant"
        assert message.content == "I am an AI assistant"
        assert message.client_msg_id == "client_123"
        assert message.message_metadata["temperature"] == 0.7
        assert message.message_metadata["model"] == "gpt-4"
    
    @pytest.mark.asyncio
    async def test_message_metadata(self, async_session):
        """Test message metadata field."""
        user = User(
            id=uuid4(),
            email="test4@example.com",
            username="testuser4",
            hashed_password="hashed123",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        chat = Chat(
            id=uuid4(),
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        message = Message(
            id=uuid4(),
            chat_id=chat.id,
            role="user",
            content="Test with metadata",
            created_at=datetime.now(timezone.utc),
            message_metadata={"key": "value", "nested": {"data": 123}}
        )
        
        async_session.add(user)
        async_session.add(chat)
        async_session.add(message)
        await async_session.commit()
        
        assert isinstance(message.message_metadata, dict)
        assert message.message_metadata["key"] == "value"
        assert message.message_metadata["nested"]["data"] == 123
