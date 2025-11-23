import pytest
from unittest.mock import Mock, patch

from src.agents.session_factory import SessionFactory, get_session_recommendations
from src.agents.context_management import TrimmingSession, SummarizingSession, HybridSession, FileBackedSession


def _build_settings():
    settings = Mock()
    settings.context_strategy = "hybrid"
    settings.context_max_turns = 8
    settings.context_keep_last_n_turns = 3
    settings.context_summary_threshold = 8
    settings.context_trim_threshold = 3
    settings.context_summary_model = "gpt-4o-mini"
    settings.context_summary_max_tokens = 400
    settings.conversations_storage_path = "/tmp/conversations"
    settings.openai_api_key = "test-key"
    return settings


def test_create_trimming_session_in_memory():
    with patch("src.agents.session_factory.get_settings") as mock_get_settings, \
         patch("src.agents.session_factory.AsyncOpenAI") as mock_async_openai:
        mock_get_settings.return_value = _build_settings()

        session = SessionFactory.create_session(
            session_id="s1",
            strategy="trimming",
            persist_to_disk=False,
            max_turns=5,
        )

        assert isinstance(session, TrimmingSession)
        assert session.max_turns == 5
        mock_async_openai.assert_not_called()


def test_create_summarizing_session_in_memory():
    with patch("src.agents.session_factory.get_settings") as mock_get_settings, \
         patch("src.agents.session_factory.AsyncOpenAI") as mock_async_openai:
        settings = _build_settings()
        mock_get_settings.return_value = settings

        session = SessionFactory.create_session(
            session_id="s2",
            strategy="summarization",
            persist_to_disk=False,
            keep_last_n_turns=2,
            context_limit=5,
            summary_model="custom-model",
            summary_max_tokens=123,
        )

        assert isinstance(session, SummarizingSession)
        mock_async_openai.assert_called_once_with(api_key=settings.openai_api_key)


def test_create_hybrid_file_backed_session(tmp_path):
    with patch("src.agents.session_factory.get_settings") as mock_get_settings, \
         patch("src.agents.session_factory.AsyncOpenAI") as mock_async_openai:
        settings = _build_settings()
        settings.conversations_storage_path = str(tmp_path)
        mock_get_settings.return_value = settings

        session = SessionFactory.create_session(
            session_id="s3",
            strategy="hybrid",
            persist_to_disk=True,
            storage_dir=str(tmp_path),
            trim_threshold=3,
            summary_threshold=6,
        )

        assert isinstance(session, FileBackedSession)
        assert session.context_strategy == "hybrid"
        assert str(session.storage_dir) == str(tmp_path)
        mock_async_openai.assert_called_once_with(api_key=settings.openai_api_key)


def test_create_session_by_type_variants():
    with patch("src.agents.session_factory.get_settings") as mock_get_settings, \
         patch("src.agents.session_factory.AsyncOpenAI"):
        mock_get_settings.return_value = _build_settings()

        research = SessionFactory.create_session_by_type("sid-r", "research", persist_to_disk=False)
        quick = SessionFactory.create_session_by_type("sid-q", "quick", persist_to_disk=False)
        analysis = SessionFactory.create_session_by_type("sid-a", "analysis", persist_to_disk=False)
        general = SessionFactory.create_session_by_type("sid-g", "general", persist_to_disk=False)
        unknown = SessionFactory.create_session_by_type("sid-u", "unknown", persist_to_disk=False)

        assert isinstance(research, HybridSession)
        assert isinstance(general, HybridSession)
        assert isinstance(quick, TrimmingSession)
        assert isinstance(analysis, SummarizingSession)
        assert isinstance(unknown, HybridSession)


def test_get_session_recommendations_and_default():
    research = get_session_recommendations("research")
    quick = get_session_recommendations("quick")
    analysis = get_session_recommendations("analysis")
    general = get_session_recommendations("general")
    fallback = get_session_recommendations("something-else")

    assert research["strategy"] == "hybrid"
    assert quick["strategy"] == "trimming"
    assert analysis["strategy"] == "summarization"
    assert general["strategy"] == "hybrid"
    assert fallback == general


def test_create_session_unknown_strategy_raises():
    with patch("src.agents.session_factory.get_settings") as mock_get_settings:
        mock_get_settings.return_value = _build_settings()

        with pytest.raises(ValueError):
            SessionFactory.create_session(
                session_id="s-unknown",
                strategy="does-not-exist",
                persist_to_disk=False,
            )
