from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from agents import Agent, ModelSettings, Runner

from src.agents.tools import search_papers, search_papers_with_graph, get_paper_details
from src.agents.prompts import RESEARCH_ASSISTANT_PROMPT
from src.agents.session_factory import SessionFactory, get_session_recommendations
from src.agents.context_management import SessionABC, FileBackedSession
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
        self._focused_papers: Dict[str, list] = {}
        self._last_focused_papers_snapshot: Dict[str, list] = {}
        
        self.conversations_dir = Path(self.settings.conversations_storage_path)
        self.conversations_dir.mkdir(exist_ok=True)
        logger.info(f"Conversations directory: {self.conversations_dir}")

        self.agent = Agent(
            name="ResearchMind Assistant",
            instructions=RESEARCH_ASSISTANT_PROMPT,
            model=self.settings.openai_model,
            tools=[search_papers, search_papers_with_graph, get_paper_details],
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
        
        logger.debug(f"Session info for {chat_id}: {info.get('user_turns', 0)} turns, {info.get('total_items', 0)} items")
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
            logger.info(f"Processing query: chat_id={chat_id}, type={conversation_type}")
            logger.debug(f"Query text: {query[:150]}{'...' if len(query) > 150 else ''}")
            
            session = self._get_or_create_session(chat_id, conversation_type)
            
            focused_papers = self.get_focused_papers(chat_id)
            
            last_snapshot = self._last_focused_papers_snapshot.get(chat_id, [])
            if sorted(last_snapshot) != sorted(focused_papers):
                from src.agents.tools import clear_tool_cache
                clear_tool_cache()
                self._last_focused_papers_snapshot[chat_id] = focused_papers.copy() if focused_papers else []
                logger.info(f"Focused papers changed for {chat_id} - cleared tool cache")
            
            context = await self._prepare_context_for_agent(session, query)
            logger.debug(f"Context prepared: has_context={context['has_context']}, history_length={len(context['history'])}")
            
            if context["has_context"]:
                recent_messages = context["history"][-2:] if len(context["history"]) >= 2 else context["history"]
                context_summary = "\n".join([
                    f"{msg.get('role', '').upper()}: {msg.get('content', '')[:150]}..."
                    for msg in recent_messages
                ])
                agent_input = f"[Previous context: {len(context['history'])} messages]\n{context_summary}\n\nCurrent query: {query}"
                logger.info(f"Using {len(context['history'])} messages as context")
            else:
                agent_input = query
                logger.info("No previous context - fresh query")
            
            if focused_papers:
                papers_info = []
                try:
                    for paper_id in focused_papers:
                        from src.services.knowledge_graph import Neo4jClient
                        with Neo4jClient() as client:
                            result = client.execute_query(
                                "MATCH (p:Paper {arxiv_id: $arxiv_id}) RETURN p.title as title",
                                {"arxiv_id": paper_id}
                            )
                            if result and result[0].get("title"):
                                papers_info.append(f"{paper_id} ({result[0]['title']})")
                            else:
                                papers_info.append(paper_id)
                except Exception as e:
                    logger.warning(f"Could not fetch paper titles: {e}")
                    papers_info = focused_papers
                
                query_lower = query.lower()
                if len(focused_papers) == 1 and any(phrase in query_lower for phrase in ["this paper", "the paper", "it ", "its "]):
                    focus_instruction = f"\n\nCRITICAL CONTEXT - FOCUSED PAPER:\nThe user is asking about THIS SPECIFIC PAPER: {papers_info[0]}\nArXiv ID: {focused_papers[0]}\n\nWhen the user says 'this paper', 'the paper', 'it', or 'its', they are referring to arXiv:{focused_papers[0]}.\nYou MUST retrieve and provide information specifically about arXiv:{focused_papers[0]}."
                else:
                    focus_instruction = f"\n\nIMPORTANT - FOCUSED PAPERS MODE:\nThe user has focused on these specific papers:\n" + "\n".join(f"- {info}" for info in papers_info) + f"\n\nYou MUST prioritize information from these papers in your response. When searching, filter results to these arXiv IDs."
                
                agent_input = agent_input + focus_instruction
                logger.info(f"Added {len(focused_papers)} focused papers to agent context: {focused_papers}")
            
            logger.info("Running agent...")
            result = await Runner.run(self.agent, agent_input)
            
            response = result.final_output or "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            logger.info(f"Agent completed - response length: {len(response)} chars")
            
            sources = []
            graph_insights = {}
            tool_calls_data = []
            
            logger.info(f"Result type: {type(result)}")
            logger.info(f"Result has messages: {hasattr(result, 'messages')}")
            logger.info(f"Result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
            
            if hasattr(result, 'messages'):
                logger.info(f"Number of messages: {len(result.messages)}")
                for i, msg in enumerate(result.messages):
                    logger.info(f"Message {i}: role={getattr(msg, 'role', 'NO_ROLE')}, type={type(msg)}")
                    
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        logger.info(f"Found tool_calls in message {i}")
                        for tool_call in msg.tool_calls:
                            tool_calls_data.append({
                                'tool': tool_call.function.name if hasattr(tool_call, 'function') else 'unknown',
                                'args': tool_call.function.arguments if hasattr(tool_call, 'function') else {}
                            })
                    
                    if hasattr(msg, 'role') and msg.role == 'tool':
                        logger.info(f"Found tool response in message {i}")
                        logger.info(f"Content type: {type(msg.content)}")
                        logger.info(f"Content preview: {str(msg.content)[:300]}")
                        try:
                            import json
                            tool_result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                            logger.info(f"Parsed tool_result type: {type(tool_result)}")
                            logger.info(f"Tool result keys: {tool_result.keys() if isinstance(tool_result, dict) else 'NOT_DICT'}")
                            
                            if isinstance(tool_result, dict):
                                if 'sources' in tool_result:
                                    found_sources = tool_result.get('sources', [])
                                    logger.info(f"{len(found_sources)} sources in tool result!")
                                    sources.extend(found_sources)
                                if 'graph_insights' in tool_result:
                                    graph_insights = tool_result.get('graph_insights', {})
                                    logger.info("Found graph_insights in tool result!")
                        except Exception as e:
                            logger.error(f"Error parsing tool response: {e}")
                            logger.debug(f"Raw content: {msg.content}")

            elif hasattr(result, 'data'):
                logger.info("Result has 'data' attribute, checking...")
                if isinstance(result.data, dict):
                    sources = result.data.get('sources', [])
                    graph_insights = result.data.get('graph_insights', {})
            elif hasattr(result, 'output'):
                logger.info("Result has 'output' attribute, checking...")
                if isinstance(result.output, dict):
                    sources = result.output.get('sources', [])
                    graph_insights = result.output.get('graph_insights', {})
            else:
                logger.warning("Result has no messages/data/output attribute!")
                
                logger.info("Attempting to use global tool cache...")
                try:
                    from src.agents.tools import get_last_tool_result
                    cached_result = get_last_tool_result()
                    if cached_result:
                        sources = cached_result.get('sources', [])
                        graph_insights = cached_result.get('graph_insights', {})
                        logger.info(f"Retrieved from cache: {len(sources)} sources")
                except Exception as e:
                    logger.error(f"Cache retrieval failed: {e}")
            
            logger.info(f"Extracted {len(sources)} sources and {len(tool_calls_data)} tool calls")
            
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
                    "timestamp": timestamp,
                    "sources": sources,
                    "graph_insights": graph_insights
                }
            ])
            
            logger.info(f"Saved interaction to session {chat_id}")
            
            session_info = await self.get_session_info(chat_id)
            logger.info(f"Updated session: {session_info.get('user_turns', 0)} turns, strategy: {session_info.get('current_strategy', 'unknown')}")
            logger.debug(f"Response preview: {response[:200]}...")
            
            return {
                "response": response,
                "sources": sources,
                "graph_insights": graph_insights,
                "tool_calls": tool_calls_data
            }
            
        except Exception as e:
            logger.error(f"Error in process_query: {e}", exc_info=True)
            
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
                logger.info(f"Cleared session for {chat_id}")
                return True
            logger.warning(f"Session {chat_id} not found for clearing")
            return False
        except Exception as e:
            logger.error(f"Error clearing session {chat_id}: {e}")
            return False
    
    async def delete_chat(self, chat_id: str) -> None:
        """Clean up agent state when a chat is deleted.
        Note: Chat persistence (database) is handled by ChatStore."""
        if chat_id in self._sessions:
            try:
                await self._sessions[chat_id].clear_session()
            except Exception:
                pass
            del self._sessions[chat_id]
        if chat_id in self._focused_papers:
            del self._focused_papers[chat_id]
        if chat_id in self._last_focused_papers_snapshot:
            del self._last_focused_papers_snapshot[chat_id]
        logger.info(f"Cleaned up agent state for deleted chat {chat_id}")
    
    def get_strategy_recommendations(self, conversation_type: str) -> Dict[str, Any]:
        """Get recommendations for context management strategy."""
        return get_session_recommendations(conversation_type)
    
    async def switch_context_strategy(self, chat_id: str, new_strategy: str) -> bool:
        """Switch context management strategy for an existing session."""
        try:
            if chat_id in self._sessions:
                logger.info(f"Switching session {chat_id} to strategy: {new_strategy}")
                current_session = self._sessions[chat_id]
                history = await current_session.get_items()
                logger.debug(f"Transferring {len(history)} items to new session")
                
                new_session = SessionFactory.create_session(
                    chat_id,
                    strategy=new_strategy,
                    storage_dir=self.conversations_dir
                )
                
                if isinstance(new_session, FileBackedSession):
                    new_session._loaded = True 

                if history:
                    await new_session.add_items(history)
                
                self._sessions[chat_id] = new_session
                logger.info(f"Successfully switched session {chat_id} to strategy: {new_strategy}")
                return True
            logger.warning(f"Session {chat_id} not found for strategy switch")
            return False
        except Exception as e:
            logger.error(f"Error switching strategy for {chat_id}: {e}")
            return False
    
    def add_focused_paper(self, chat_id: str, arxiv_id: str) -> None:
        """Add a paper to the focused list for this session (idempotent - prevents duplicates)."""
        if chat_id not in self._focused_papers:
            self._focused_papers[chat_id] = []
        
        if arxiv_id not in self._focused_papers[chat_id]:
            self._focused_papers[chat_id].append(arxiv_id)
            logger.info(f"✅ Focused on paper {arxiv_id} for chat {chat_id}")
        else:
            logger.info(f"⚠️ Paper {arxiv_id} already focused for chat {chat_id} - skipping duplicate")
    
    def remove_focused_paper(self, chat_id: str, arxiv_id: str) -> None:
        """Remove a paper from the focused list (idempotent: removes all occurrences)."""
        logger.info(f"Attempting to unfocus paper {arxiv_id} for chat {chat_id}")
        logger.info(f"Current focused papers before removal: {self._focused_papers.get(chat_id, [])}")
        
        if chat_id in self._focused_papers and self._focused_papers[chat_id]:
            before = len(self._focused_papers[chat_id])
            self._focused_papers[chat_id] = [p for p in self._focused_papers[chat_id] if p != arxiv_id]
            after = len(self._focused_papers[chat_id])
            removed = before - after
            
            logger.info(f"Focused papers after removal: {self._focused_papers[chat_id]}")
            
            if removed > 0:
                logger.info(f"✅ Unfocused paper {arxiv_id} for chat {chat_id} (removed {removed} occurrence(s))")
            else:
                logger.warning(f"⚠️ Paper {arxiv_id} not present in focused list for chat {chat_id}")
        else:
            logger.warning(f"⚠️ No focused papers found for chat {chat_id}")
    
    def clear_focused_papers(self, chat_id: str) -> None:
        """Clear all focused papers for this session."""
        if chat_id in self._focused_papers:
            count = len(self._focused_papers[chat_id])
            self._focused_papers[chat_id] = []
            logger.info(f"Cleared {count} focused papers for chat {chat_id}")
    
    def get_focused_papers(self, chat_id: str) -> list:
        """Get list of focused paper IDs for this session (frontend is the source of truth)."""
        return self._focused_papers.get(chat_id, [])


logger.info("Creating shared BaseAgent instance")
retrieval_agent = BaseAgent()
logger.info("Shared BaseAgent instance created successfully")
