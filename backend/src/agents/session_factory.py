"""
Session factory for creating appropriate context management sessions
based on configuration and use case requirements.
"""

from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from src.config import get_settings
from src.agents.context_management import (
    SessionABC,
    TrimmingSession,
    SummarizingSession,
    HybridSession,
    FileBackedSession,
    LLMSummarizer,
)


class SessionFactory:
    """Factory for creating context management sessions."""
    
    @staticmethod
    def create_session(
        session_id: str,
        strategy: Optional[str] = None,
        persist_to_disk: bool = True,
        **kwargs
    ) -> SessionABC:
        """
        Create a context management session based on strategy and configuration.
        
        Args:
            session_id: Unique identifier for the session
            strategy: Context management strategy ("trimming", "summarization", "hybrid", or None for config default)
            persist_to_disk: Whether to persist conversation history to disk
            **kwargs: Additional parameters for session configuration
            
        Returns:
            Configured session instance
        """
        settings = get_settings()
        
        strategy = strategy or settings.context_strategy
        
        openai_client = None
        if strategy in ("summarization", "hybrid") and settings.openai_api_key:
            openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        summarizer = None
        if strategy in ("summarization", "hybrid"):
            summarizer = LLMSummarizer(
                client=openai_client,
                model=kwargs.get("summary_model", settings.context_summary_model),
                max_tokens=kwargs.get("summary_max_tokens", settings.context_summary_max_tokens),
                tool_trim_limit=kwargs.get("tool_trim_limit", 600),
            )
        
        session_params = {
            "session_id": session_id,
        }
        
        if strategy == "trimming":
            session_params["max_turns"] = kwargs.get("max_turns", settings.context_max_turns)
            session_class = TrimmingSession
            
        elif strategy == "summarization":
            session_params.update({
                "keep_last_n_turns": kwargs.get("keep_last_n_turns", settings.context_keep_last_n_turns),
                "context_limit": kwargs.get("context_limit", settings.context_summary_threshold),
                "summarizer": summarizer,
            })
            session_class = SummarizingSession
            
        elif strategy == "hybrid":
            session_params.update({
                "trim_threshold": kwargs.get("trim_threshold", settings.context_trim_threshold),
                "summary_threshold": kwargs.get("summary_threshold", settings.context_summary_threshold),
                "keep_last_n_turns": kwargs.get("keep_last_n_turns", settings.context_keep_last_n_turns),
                "summarizer": summarizer,
            })
            session_class = HybridSession
            
        else:
            raise ValueError(f"Unknown context strategy: {strategy}")
        
        if persist_to_disk:
            return FileBackedSession(
                session_id=session_id,
                storage_dir=kwargs.get("storage_dir", settings.conversations_storage_path),
                context_strategy=strategy,
                **{k: v for k, v in session_params.items() if k != "session_id"}
            )
        else:
            return session_class(**session_params)
    
    @staticmethod
    def create_research_session(session_id: str, **kwargs) -> SessionABC:
        """
        Create a session optimized for research conversations.
        
        Research sessions typically benefit from summarization to maintain
        long-term context about papers, findings, and research directions.
        """
        return SessionFactory.create_session(
            session_id=session_id,
            strategy="hybrid",
            summary_threshold=8,
            keep_last_n_turns=3,
            **kwargs
        )
    
    @staticmethod
    def create_quick_session(session_id: str, **kwargs) -> SessionABC:
        """
        Create a session optimized for quick, independent queries.
        
        Quick sessions use trimming for fast, stateless-like interactions.
        """
        return SessionFactory.create_session(
            session_id=session_id,
            strategy="trimming",
            max_turns=5,
            **kwargs
        )
    
    @staticmethod
    def create_analysis_session(session_id: str, **kwargs) -> SessionABC:
        """
        Create a session optimized for deep paper analysis.
        
        Analysis sessions use summarization to maintain detailed context
        about papers being analyzed over long conversations.
        """
        return SessionFactory.create_session(
            session_id=session_id,
            strategy="summarization",
            keep_last_n_turns=4,
            context_limit=10,
            **kwargs
        )
    
    @staticmethod
    def create_session_by_type(session_id: str, conversation_type: str, **kwargs) -> SessionABC:
        """
        Create a session based on conversation type.
        
        Args:
            session_id: Unique identifier for the session
            conversation_type: Type of conversation ("research", "quick", "analysis", "general")
            **kwargs: Additional parameters for session configuration
            
        Returns:
            Configured session instance
        """
        type_map = {
            "research": SessionFactory.create_research_session,
            "quick": SessionFactory.create_quick_session,
            "analysis": SessionFactory.create_analysis_session,
            "general": lambda sid, **kw: SessionFactory.create_session(sid, strategy="hybrid", **kw),
        }
        
        creator = type_map.get(conversation_type, type_map["general"])
        return creator(session_id, **kwargs)


def get_session_recommendations(conversation_type: str) -> Dict[str, Any]:
    """
    Get recommended session configuration for different conversation types.
    
    Args:
        conversation_type: Type of conversation ("research", "quick", "analysis", "general")
        
    Returns:
        Dictionary with recommended configuration parameters
    """
    recommendations = {
        "research": {
            "strategy": "hybrid",
            "description": "Best for research conversations with mixed short/long interactions",
            "trim_threshold": 3,
            "summary_threshold": 8,
            "keep_last_n_turns": 3,
            "benefits": [
                "Maintains research context across sessions",
                "Efficient for both quick queries and deep analysis",
                "Preserves paper references and findings"
            ]
        },
        
        "quick": {
            "strategy": "trimming",
            "description": "Optimized for fast, independent queries",
            "max_turns": 5,
            "benefits": [
                "Low latency responses",
                "No summarization overhead",
                "Good for simple Q&A"
            ]
        },
        
        "analysis": {
            "strategy": "summarization",
            "description": "Deep paper analysis with detailed context retention",
            "keep_last_n_turns": 4,
            "context_limit": 10,
            "benefits": [
                "Retains detailed analysis context",
                "Good for literature reviews",
                "Maintains paper relationships"
            ]
        },
        
        "general": {
            "strategy": "hybrid",
            "description": "Balanced approach for mixed conversation types",
            "trim_threshold": 5,
            "summary_threshold": 12,
            "keep_last_n_turns": 4,
            "benefits": [
                "Adapts to conversation length",
                "Good default choice",
                "Balances efficiency and context retention"
            ]
        }
    }
    
    return recommendations.get(conversation_type, recommendations["general"])
