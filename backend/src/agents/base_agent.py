from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from agents import Agent, ModelSettings, Runner

from src.agents.tools import search_papers
from src.agents.prompts import RESEARCH_ASSISTANT_PROMPT
from src.agents.session_factory import SessionFactory, get_session_recommendations
from src.agents.context_management import SessionABC
from src.config import get_settings
from src.core import logger

from dotenv import load_dotenv
load_dotenv()

class BaseAgent:
    """
    Intelligent research assistant with advanced context management.
    
    Uses OpenAI Agents SDK with intelligent context management strategies:
    - Summarization: For deep analysis requiring long-term context
    - Hybrid: Adaptive strategy that switches based on conversation complexity
    """

    def __init__(self, context_strategy: Optional[str] = None):
        logger.info("Initializing BaseAgent")
        self.settings = get_settings()
        self.context_strategy = context_strategy or self.settings.context_strategy
        
        self._sessions: Dict[str, SessionABC] = {}
        
        self.conversations_dir = Path(self.settings.conversations_storage_path)
        self.conversations_dir.mkdir(exist_ok=True)
        logger.info(f"Conversations directory: {self.conversations_dir}")

        self.agent = Agent(
            name="ResearchMind Assistant",
            instructions=RESEARCH_ASSISTANT_PROMPT,
            model=self.settings.openai_model,
            tools=[search_papers],
            model_settings=ModelSettings(
                tool_choice="auto",
            ),
        )
        
        print(f"BaseAgent initialized with context strategy: {self.context_strategy}")
    
    def _get_or_create_session(self, chat_id: str, conversation_type: str) -> SessionABC:
        """Get existing session or create a new one based on conversation type."""
        if chat_id not in self._sessions:
            logger.info(f"Creating new session: chat_id={chat_id}, type={conversation_type}")
            session = SessionFactory.create_session_by_type(
                chat_id, 
                conversation_type,
                storage_dir=self.conversations_dir
            )
            self._sessions[chat_id] = session
            logger.info(f"Session created successfully")
        else:
            logger.debug(f"Reusing existing session: {chat_id}")
        
        return self._sessions[chat_id]
    
    async def get_session_info(self, chat_id: str) -> Dict[str, Any]:
        """Get detailed information about a session."""
        if chat_id not in self._sessions:
            logger.debug(f"No session found for chat_id: {chat_id}")
            return {"status": "no_session", "chat_id": chat_id}
        
        session = self._sessions[chat_id]
        items = await session.get_items()
        
        info = {
            "chat_id": chat_id,
            "status": "active",
            "total_items": len(items),
            "user_turns": len([item for item in items if item.get("role") == "user"]),
        }
        
        if hasattr(session, 'get_session_info'):
            session_info = await session.get_session_info()
            info.update(session_info)
        elif hasattr(session, 'get_strategy_info'):
            strategy_info = await session.get_strategy_info()
            info.update(strategy_info)
        
        logger.debug(f"📊 Session info for {chat_id}: {info.get('user_turns', 0)} turns, {info.get('total_items', 0)} items")
        return info
    
    async def _prepare_context_for_agent(self, session: SessionABC, query: str) -> Dict[str, Any]:
        """Prepare context for the agent using intelligent session management.
        
        Returns a dict with the query and conversation history.
        The session has already handled context management (trimming/summarization).
        """
        history = await session.get_items()
        
        context = {
            "query": query,
            "history": history,
            "has_context": len(history) > 0
        }
        
        if history:
            context["context_note"] = f"This is a continuation of a {len(history)}-message conversation."
        
        return context


    async def process_query(
        self, 
        query: str, 
        chat_id: str, 
        conversation_type: str = "research",
        **kwargs
    ) -> str:
        """
        Process a user query with intelligent context management.
        
        Args:
            query: User's question or request
            chat_id: Unique conversation identifier
            conversation_type: Type of conversation ("research", "quick", "analysis", "general")
            **kwargs: Additional parameters for session configuration
            
        Returns:
            Agent's response as a string
        """
        try:
            logger.info(f"🔍 Processing query: chat_id={chat_id}, type={conversation_type}")
            logger.debug(f"💬 Query text: {query[:150]}{'...' if len(query) > 150 else ''}")
            
            session = self._get_or_create_session(chat_id, conversation_type)
            
            context = await self._prepare_context_for_agent(session, query)
            logger.debug(f"📝 Context prepared: has_context={context['has_context']}, history_length={len(context['history'])}")
            
            if context["has_context"]:
                recent_messages = context["history"][-2:] if len(context["history"]) >= 2 else context["history"]
                context_summary = "\n".join([
                    f"{msg.get('role', '').upper()}: {msg.get('content', '')[:150]}..."
                    for msg in recent_messages
                ])
                agent_input = f"[Previous context: {len(context['history'])} messages]\n{context_summary}\n\nCurrent query: {query}"
                logger.info(f"🧠 Using {len(context['history'])} messages as context")
            else:
                agent_input = query
                logger.info("🆕 No previous context - fresh query")
            
            logger.info("🤖 Running agent...")
            result = await Runner.run(self.agent, agent_input)
            
            response = result.final_output or "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            logger.info(f"✅ Agent completed - response length: {len(response)} chars")
            
            timestamp = datetime.now().isoformat()
            
            await session.add_items([
                {
                    "role": "user",
                    "content": query,
                    "timestamp": timestamp
                },
                {
                    "role": "assistant", 
                    "content": response,
                    "timestamp": timestamp
                }
            ])
            
            logger.info(f"💾 Saved interaction to session {chat_id}")
            
            session_info = await self.get_session_info(chat_id)
            logger.info(f"📊 Updated session: {session_info.get('user_turns', 0)} turns, strategy: {session_info.get('current_strategy', 'unknown')}")
            logger.debug(f"📤 Response preview: {response[:200]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in process_query: {e}", exc_info=True)
            
            try:
                from src.agents.tools import search_papers
                search_results = search_papers(query, limit=3)
                if search_results:
                    fallback_response = f"I found some relevant papers for your query '{query}'. Here are the top results: {search_results}"
                    
                    try:
                        session = self._get_or_create_session(chat_id, conversation_type)
                        await session.add_items([{
                            "role": "user",
                            "content": query,
                            "timestamp": datetime.now().isoformat()
                        }, {
                            "role": "assistant",
                            "content": fallback_response,
                            "timestamp": datetime.now().isoformat()
                        }])
                    except:
                        pass
                    
                    return fallback_response
                else:
                    return f"I encountered an issue processing your query '{query}', but I'm working to resolve it. Please try a simpler question."
            except:
                return f"I'm currently experiencing technical difficulties. Please try again with a simpler query."
    
    async def clear_session(self, chat_id: str) -> bool:
        """Clear a conversation session."""
        try:
            if chat_id in self._sessions:
                await self._sessions[chat_id].clear_session()
                del self._sessions[chat_id]
                logger.info(f"🗑️ Cleared session for {chat_id}")
                return True
            logger.warning(f"⚠️ Session {chat_id} not found for clearing")
            return False
        except Exception as e:
            logger.error(f"❌ Error clearing session {chat_id}: {e}")
            return False
    
    def get_strategy_recommendations(self, conversation_type: str) -> Dict[str, Any]:
        """Get recommendations for context management strategy."""
        return get_session_recommendations(conversation_type)
    
    async def switch_context_strategy(self, chat_id: str, new_strategy: str) -> bool:
        """Switch context management strategy for an existing session."""
        try:
            if chat_id in self._sessions:
                logger.info(f"🔄 Switching session {chat_id} to strategy: {new_strategy}")
                current_session = self._sessions[chat_id]
                history = await current_session.get_items()
                logger.debug(f"📜 Transferring {len(history)} items to new session")
                
                new_session = SessionFactory.create_session(
                    chat_id,
                    strategy=new_strategy,
                    storage_dir=self.conversations_dir
                )
                
                if history:
                    await new_session.add_items(history)
                
                self._sessions[chat_id] = new_session
                logger.info(f"✅ Successfully switched session {chat_id} to strategy: {new_strategy}")
                return True
            logger.warning(f"⚠️ Session {chat_id} not found for strategy switch")
            return False
        except Exception as e:
            logger.error(f"❌ Error switching strategy for {chat_id}: {e}")
            return False
