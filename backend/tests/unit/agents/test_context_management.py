import pytest
import json
from unittest.mock import Mock, AsyncMock
from src.agents.context_management import (
    TrimmingSession, SummarizingSession, HybridSession, FileBackedSession, LLMSummarizer
)

@pytest.mark.asyncio
async def test_trimming_session():
    """Test TrimmingSession logic."""
    session = TrimmingSession("s1", max_turns=2)
    
    await session.add_items([{"role": "user", "content": "u1"}])
    await session.add_items([{"role": "assistant", "content": "a1"}])
    
    await session.add_items([{"role": "user", "content": "u2"}])
    await session.add_items([{"role": "assistant", "content": "a2"}])
    
    items = await session.get_items()
    assert len(items) == 4
    assert items[0]["content"] == "u1"
    
    await session.add_items([{"role": "user", "content": "u3"}])
    
    items = await session.get_items()
    assert len(items) == 3
    assert items[0]["content"] == "u2"
    
    await session.add_items([{"role": "assistant", "content": "a3"}])
    items = await session.get_items()
    assert len(items) == 4

@pytest.mark.asyncio
async def test_llm_summarizer():
    """Test LLMSummarizer."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Summary"))]
    mock_client.chat.completions.create.return_value = mock_response
    
    summarizer = LLMSummarizer(client=mock_client)
    
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"}
    ]
    
    user_shadow, summary = await summarizer.summarize(messages)
    
    assert user_shadow == "Summarize our conversation so far."
    assert summary == "Summary"
    mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_summarizing_session():
    """Test SummarizingSession logic."""
    mock_summarizer = Mock(spec=LLMSummarizer)
    mock_summarizer.summarize = AsyncMock(return_value=("Shadow User", "Summary Content"))
    
    session = SummarizingSession("s2", keep_last_n_turns=1, context_limit=2, summarizer=mock_summarizer)
    
    await session.add_items([{"role": "user", "content": "u1"}])
    await session.add_items([{"role": "assistant", "content": "a1"}])
    
    await session.add_items([{"role": "user", "content": "u2"}])
    await session.add_items([{"role": "assistant", "content": "a2"}])
    
    items = await session.get_items()
    assert len(items) == 4
    
    await session.add_items([{"role": "user", "content": "u3"}])
    
    items = await session.get_items()
    
    assert len(items) == 3
    assert items[0]["content"] == "Shadow User"
    assert items[1]["content"] == "Summary Content"
    assert items[2]["content"] == "u3"
    
    mock_summarizer.summarize.assert_called_once()

@pytest.mark.asyncio
async def test_hybrid_session():
    """Test HybridSession switching."""
    mock_summarizer = Mock(spec=LLMSummarizer)
    mock_summarizer.summarize = AsyncMock(return_value=("Shadow User", "Summary Content"))

    session = HybridSession("s3", trim_threshold=2, summary_threshold=4, keep_last_n_turns=1, summarizer=mock_summarizer)
    
    assert session._strategy == "trimming"
    assert isinstance(session._current_session, TrimmingSession)

    for i in range(3):
        await session.add_items([{"role": "user", "content": f"u{i}"}])
        await session.add_items([{"role": "assistant", "content": f"a{i}"}])
        
    items = await session.get_items()

    assert len(items) == 4
    assert items[0]["content"] == "u1"
    
    info = await session.get_strategy_info()
    assert info["current_strategy"] == "trimming"

    session2 = HybridSession("s3b", trim_threshold=4, summary_threshold=2, keep_last_n_turns=1, summarizer=mock_summarizer)
    for i in range(3):
        await session2.add_items([{"role": "user", "content": f"u{i}"}])
        await session2.add_items([{"role": "assistant", "content": f"a{i}"}])
        
    info2 = await session2.get_strategy_info()
    assert info2["current_strategy"] == "summarization"
    assert info2["user_turns"] >= 2
    assert info2.get("synthetic_items", 0) >= 2

@pytest.mark.asyncio
async def test_trimming_session_dynamic_turns():
    session = TrimmingSession("s-dynamic", max_turns=3)

    for i in range(3):
        await session.add_items([{"role": "user", "content": f"u{i}"}])
        await session.add_items([{"role": "assistant", "content": f"a{i}"}])

    items = await session.get_items()
    assert len(items) == 6

    await session.set_max_turns(1)
    items_after = await session.get_items()
    assert len(items_after) == 2
    assert items_after[0]["content"] == "u2"
    assert items_after[1]["content"] == "a2"

    raw = await session.raw_items()
    assert raw == items_after

@pytest.mark.asyncio
async def test_file_backed_session(tmp_path):
    """Test FileBackedSession persistence."""
    storage_dir = tmp_path / "conversations"
    session = FileBackedSession("s4", storage_dir=storage_dir, context_strategy="trimming", max_turns=5)
    
    await session.add_items([{"role": "user", "content": "u1"}])
    
    file_path = storage_dir / "s4.json"
    assert file_path.exists()
    
    with open(file_path, "r") as f:
        data = json.load(f)
        assert len(data["items"]) == 1
        assert data["items"][0]["content"] == "u1"
    
    session2 = FileBackedSession("s4", storage_dir=storage_dir, context_strategy="trimming", max_turns=5)
    items = await session2.get_items()
    assert len(items) == 1
    assert items[0]["content"] == "u1"
    
    info = await session.get_session_info()
    assert info["session_id"] == "s4"
    assert info["file_exists"] is True
    assert info["current_strategy"] == "trimming"
    
    await session.clear_session()
    assert not file_path.exists()
    info_after = await session.get_session_info()
    assert info_after["file_exists"] is False
