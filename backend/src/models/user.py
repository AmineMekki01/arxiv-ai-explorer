import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy import TypeDecorator, JSON
from src.database import Base
import json


class StringArray(TypeDecorator):
    """Custom type that stores array as JSON for SQLite, ARRAY for PostgreSQL."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if dialect.name == 'postgresql':
            return value if value is not None else []
        else:
            try:
                return json.loads(value) if value else []
            except (json.JSONDecodeError, TypeError):
                return []


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user")


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    preferred_categories = Column(StringArray, nullable=False, default=list)
    
    theme = Column(String, default="light", nullable=False)
    items_per_page = Column(String, default="10", nullable=False)
    
    email_notifications = Column(Boolean, default=True, nullable=False)
    
    default_search_limit = Column(String, default="10", nullable=False)
    default_context_strategy = Column(String, default="trimming", nullable=False)
    
    custom_settings = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="preferences")

