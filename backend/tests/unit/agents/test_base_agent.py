import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from src.agents.base_agent import BaseAgent
from src.agents.context_management import SessionABC

@pytest.fixture
def mock_settings():
    """Mock settings."""
    with patch("src.agents.base_agent.get_settings") as mock:
        settings = Mock()
        settings.context_strategy = "hybrid"
        settings.conversations_storage_path = "/tmp/conversations"
        settings.openai_model = "gpt-4"
        mock.return_value = settings
        yield settings

@pytest.fixture
def mock_agent_cls():
    """Mock Agent class."""
    with patch("src.agents.base_agent.Agent") as mock:
        yield mock

@pytest.fixture
def mock_runner():
    """Mock Runner class."""
    with patch("src.agents.base_agent.Runner") as mock:
        yield mock

@pytest.fixture
def mock_session_factory():
    """Mock SessionFactory."""
    with patch("src.agents.base_agent.SessionFactory") as mock:
        yield mock

@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4jClient."""
    with patch("src.services.knowledge_graph.Neo4jClient") as mock:
        yield mock

@pytest.fixture
def base_agent(mock_settings, mock_agent_cls, mock_runner, mock_session_factory):
    """Create BaseAgent instance."""
    with patch("src.agents.base_agent.Path") as mock_path:
        mock_path.return_value.mkdir = Mock()
        agent = BaseAgent()
        return agent

@pytest.mark.asyncio
async def test_init(base_agent, mock_settings, mock_agent_cls):
    """Test initialization."""
    assert base_agent.context_strategy == "hybrid"
    assert base_agent._sessions == {}
    mock_agent_cls.assert_called_once()

@pytest.mark.asyncio
async def test_get_or_create_session_new(base_agent, mock_session_factory):
    """Test creating a new session."""
    mock_session = Mock(spec=SessionABC)
    mock_session_factory.create_session_by_type.return_value = mock_session
    
    session = base_agent._get_or_create_session("chat1", "research")
    
    assert session == mock_session
    assert base_agent._sessions["chat1"] == mock_session
    mock_session_factory.create_session_by_type.assert_called_once_with(
        "chat1", "research", storage_dir=base_agent.conversations_dir
    )

@pytest.mark.asyncio
async def test_get_or_create_session_existing(base_agent, mock_session_factory):
    """Test retrieving an existing session."""
    mock_session = Mock(spec=SessionABC)
    base_agent._sessions["chat1"] = mock_session
    
    session = base_agent._get_or_create_session("chat1", "research")
    
    assert session == mock_session
    mock_session_factory.create_session_by_type.assert_not_called()

@pytest.mark.asyncio
async def test_process_query(base_agent, mock_runner, mock_session_factory):
    """Test processing a query."""
    mock_session = AsyncMock(spec=SessionABC)
    mock_session.get_items.return_value = []
    mock_session.add_items = AsyncMock()
    mock_session_factory.create_session_by_type.return_value = mock_session
    
    mock_result = Mock()
    mock_result.final_output = "Response"
    mock_runner.run = AsyncMock(return_value=mock_result)
    
    with patch("src.agents.tools.clear_tool_cache"), \
         patch("src.agents.tools.get_all_tool_results", return_value=[]), \
         patch("src.agents.tools.get_last_tool_result", return_value=None):
        
        result = await base_agent.process_query("Hello", "chat1")
        
        assert result["response"] == "Response"
        mock_runner.run.assert_called_once()
        mock_session.add_items.assert_called_once()

@pytest.mark.asyncio
async def test_process_query_with_focused_papers(base_agent, mock_runner, mock_session_factory):
    """Test processing a query with focused papers."""
    mock_session = AsyncMock(spec=SessionABC)
    mock_session.get_items.return_value = []
    mock_session.add_items = AsyncMock()
    mock_session_factory.create_session_by_type.return_value = mock_session
    
    mock_result = Mock()
    mock_result.final_output = "Response"
    mock_runner.run = AsyncMock(return_value=mock_result)
    
    base_agent.add_focused_paper("chat1", "2301.00001")
    
    with patch("src.agents.tools.clear_tool_cache"), \
         patch("src.agents.tools.get_all_tool_results", return_value=[]), \
         patch("src.agents.tools.get_last_tool_result", return_value=None), \
         patch("src.services.knowledge_graph.Neo4jClient") as mock_neo4j:
             
        mock_client = MagicMock()
        mock_neo4j.return_value.__enter__.return_value = mock_client
        mock_client.execute_query.return_value = [{"title": "Test Paper"}]
        
        result = await base_agent.process_query("Hello", "chat1")
        
        assert result["response"] == "Response"

        args, _ = mock_runner.run.call_args
        assert "IMPORTANT - FOCUSED PAPERS MODE" in args[1]
        assert "2301.00001" in args[1]

@pytest.mark.asyncio
async def test_clear_session(base_agent):
    """Test clearing a session."""
    mock_session = AsyncMock(spec=SessionABC)
    base_agent._sessions["chat1"] = mock_session
    
    success = await base_agent.clear_session("chat1")
    
    assert success is True
    assert "chat1" not in base_agent._sessions
    mock_session.clear_session.assert_called_once()


@pytest.mark.asyncio
async def test_clear_session_not_found(base_agent):
    """clear_session should return False when session does not exist."""
    success = await base_agent.clear_session("missing")

    assert success is False

@pytest.mark.asyncio
async def test_delete_chat(base_agent):
    """Test deleting a chat."""
    mock_session = AsyncMock(spec=SessionABC)
    base_agent._sessions["chat1"] = mock_session
    base_agent.add_focused_paper("chat1", "2301.00001")
    
    await base_agent.delete_chat("chat1")
    
    assert "chat1" not in base_agent._sessions
    assert "chat1" not in base_agent._focused_papers
    mock_session.clear_session.assert_called_once()

@pytest.mark.asyncio
async def test_focused_papers_management(base_agent):
    """Test adding, removing, and clearing focused papers."""
    base_agent.add_focused_paper("chat1", "p1")
    assert base_agent.get_focused_papers("chat1") == ["p1"]
    
    base_agent.add_focused_paper("chat1", "p1")
    assert base_agent.get_focused_papers("chat1") == ["p1"]
    
    base_agent.add_focused_paper("chat1", "p2")
    assert base_agent.get_focused_papers("chat1") == ["p1", "p2"]
    
    base_agent.remove_focused_paper("chat1", "p1")
    assert base_agent.get_focused_papers("chat1") == ["p2"]
    
    base_agent.clear_focused_papers("chat1")
    assert base_agent.get_focused_papers("chat1") == []


@pytest.mark.asyncio
async def test_get_session_info_no_session(base_agent):
    """get_session_info should indicate when no session exists."""
    info = await base_agent.get_session_info("unknown")

    assert info["status"] == "no_session"
    assert info["chat_id"] == "unknown"


@pytest.mark.asyncio
async def test_get_session_info_with_strategy_info(base_agent):
    """get_session_info should merge strategy info when available."""
    class DummySession:
        async def get_items(self):
            return [{"role": "user", "content": "hi"}]

        async def get_strategy_info(self):
            return {"current_strategy": "hybrid", "extra": "value"}

    base_agent._sessions["chat1"] = DummySession()

    info = await base_agent.get_session_info("chat1")

    assert info["status"] == "active"
    assert info["total_items"] == 1
    assert info["user_turns"] == 1
    assert info["current_strategy"] == "hybrid"
    assert info["extra"] == "value"


def test_get_strategy_recommendations(base_agent):
    """Verify BaseAgent delegates to get_session_recommendations."""
    with patch("src.agents.base_agent.get_session_recommendations") as mock_get:
        mock_get.return_value = {"strategy": "hybrid"}

        result = base_agent.get_strategy_recommendations("research")

        mock_get.assert_called_once_with("research")
        assert result["strategy"] == "hybrid"


@pytest.mark.asyncio
async def test_switch_context_strategy_success(base_agent, mock_session_factory):
    """Switching strategy should create a new session and transfer history."""
    mock_current = AsyncMock(spec=SessionABC)
    history = [{"role": "user", "content": "hi"}]
    mock_current.get_items.return_value = history
    base_agent._sessions["chat1"] = mock_current

    mock_new = AsyncMock(spec=SessionABC)
    mock_session_factory.create_session.return_value = mock_new

    success = await base_agent.switch_context_strategy("chat1", "summarization")

    assert success is True
    mock_session_factory.create_session.assert_called_once()
    mock_new.add_items.assert_awaited_once_with(history)
    assert base_agent._sessions["chat1"] is mock_new


@pytest.mark.asyncio
async def test_switch_context_strategy_no_session(base_agent, mock_session_factory):
    """Switching strategy for missing session should return False."""
    success = await base_agent.switch_context_strategy("missing", "summarization")

    assert success is False
    mock_session_factory.create_session.assert_not_called()


@pytest.mark.asyncio
async def test_process_query_fallback_on_error(base_agent, mock_runner, mock_session_factory):
    """When process_query errors, it should use search_papers_with_graph fallback."""
    mock_session = AsyncMock(spec=SessionABC)
    mock_session.get_items.return_value = []
    mock_session.add_items = AsyncMock()
    mock_session_factory.create_session_by_type.return_value = mock_session

    mock_runner.run = AsyncMock(side_effect=Exception("agent failure"))

    with patch("src.agents.tools.search_papers_with_graph") as mock_search:
        mock_search.return_value = {"results": ["paper1", "paper2"]}

        result = await base_agent.process_query("Hello", "chat1")

        assert "relevant papers" in result
        mock_search.assert_called_once()
