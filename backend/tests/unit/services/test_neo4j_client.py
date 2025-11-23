import pytest
from unittest.mock import Mock, patch, MagicMock
from src.services.knowledge_graph.neo4j_client import Neo4jClient, close_shared_driver

@pytest.fixture
def mock_settings():
    """Mock settings."""
    with patch("src.services.knowledge_graph.neo4j_client.get_settings") as mock:
        mock.return_value.neo4j_uri = "bolt://localhost:7687"
        mock.return_value.neo4j_user = "neo4j"
        mock.return_value.neo4j_password = "password"
        mock.return_value.neo4j_database = "neo4j"
        yield mock

@pytest.fixture
def mock_driver():
    """Mock Neo4j driver."""
    with patch("src.services.knowledge_graph.neo4j_client.GraphDatabase.driver") as mock:
        driver_instance = MagicMock()
        mock.return_value = driver_instance
        
        session_instance = MagicMock()
        driver_instance.session.return_value.__enter__.return_value = session_instance
        
        yield driver_instance, session_instance

@pytest.fixture
def client(mock_settings, mock_driver):
    """Create a Neo4jClient instance."""
    close_shared_driver()
    return Neo4jClient()

class TestNeo4jClient:
    """Tests for Neo4jClient."""

    def test_connect(self, client, mock_driver):
        """Test connecting to Neo4j."""
        driver_mock, _ = mock_driver
        
        client.connect()
        
        assert client.driver is not None
        assert client.driver == driver_mock

    def test_execute_query(self, client, mock_driver):
        """Test executing a query."""
        driver_mock, session_mock = mock_driver
        
        record = {"key": "value"}
        result_mock = MagicMock()
        result_mock.__iter__.return_value = [record]
        session_mock.run.return_value = result_mock
        
        client.connect()
        
        session_mock.run.reset_mock()
        
        results = client.execute_query("MATCH (n) RETURN n")
        
        assert len(results) == 1
        assert results[0] == record
        session_mock.run.assert_called_once()

    def test_execute_write(self, client, mock_driver):
        """Test executing a write transaction."""
        driver_mock, session_mock = mock_driver
        
        summary_mock = Mock()
        summary_mock.counters.nodes_created = 1
        summary_mock.counters.relationships_created = 0
        summary_mock.counters.properties_set = 0
        summary_mock.counters.labels_added = 0
        
        result_mock = Mock()
        result_mock.consume.return_value = summary_mock
        session_mock.run.return_value = result_mock
        
        client.connect()
        
        session_mock.run.reset_mock()
        
        stats = client.execute_write("CREATE (n)")
        
        assert stats["nodes_created"] == 1
        session_mock.run.assert_called_once()

    def test_create_constraints(self, client, mock_driver):
        """Test creating constraints."""
        driver_mock, session_mock = mock_driver
        
        summary_mock = Mock()
        summary_mock.counters.nodes_created = 0
        summary_mock.counters.relationships_created = 0
        summary_mock.counters.properties_set = 0
        summary_mock.counters.labels_added = 0
        
        result_mock = Mock()
        result_mock.consume.return_value = summary_mock
        session_mock.run.return_value = result_mock
        
        client.connect()
        session_mock.run.reset_mock()
        
        client.create_constraints()
        
        assert session_mock.run.call_count >= 1

    def test_create_indexes(self, client, mock_driver):
        """Test creating indexes."""
        driver_mock, session_mock = mock_driver
        
        summary_mock = Mock()
        summary_mock.counters.nodes_created = 0
        summary_mock.counters.relationships_created = 0
        summary_mock.counters.properties_set = 0
        summary_mock.counters.labels_added = 0
        
        result_mock = Mock()
        result_mock.consume.return_value = summary_mock
        session_mock.run.return_value = result_mock
        
        client.connect()
        session_mock.run.reset_mock()
        
        client.create_indexes()
        
        assert session_mock.run.call_count >= 1

    def test_initialize_schema(self, client, mock_driver):
        """Test initializing schema."""
        driver_mock, session_mock = mock_driver
        
        summary_mock = Mock()
        summary_mock.counters.nodes_created = 0
        summary_mock.counters.relationships_created = 0
        summary_mock.counters.properties_set = 0
        summary_mock.counters.labels_added = 0
        
        result_mock = Mock()
        result_mock.consume.return_value = summary_mock
        session_mock.run.return_value = result_mock
        
        client.connect()
        session_mock.run.reset_mock()
        
        client.initialize_schema()
        
        assert session_mock.run.call_count >= 1

    def test_clear_database(self, client, mock_driver):
        """Test clearing database."""
        driver_mock, session_mock = mock_driver
        
        summary_mock = Mock()
        summary_mock.counters.nodes_created = 0
        summary_mock.counters.relationships_created = 0
        summary_mock.counters.properties_set = 0
        summary_mock.counters.labels_added = 0
        
        result_mock = Mock()
        result_mock.consume.return_value = summary_mock
        session_mock.run.return_value = result_mock
        
        client.connect()
        session_mock.run.reset_mock()
        
        client.clear_database()
        
        session_mock.run.assert_called_once()
        assert "DETACH DELETE" in session_mock.run.call_args[0][0]

    def test_get_stats(self, client, mock_driver):
        """Test getting stats."""
        driver_mock, session_mock = mock_driver
        
        records = [
            {"node_type": "Paper", "count": 10},
            {"node_type": "CITES", "count": 5}
        ]
        result_mock = MagicMock()
        result_mock.__iter__.return_value = records
        session_mock.run.return_value = result_mock
        
        client.connect()
        session_mock.run.reset_mock()
        
        stats = client.get_stats()
        
        assert stats["nodes"]["Paper"] == 10
        assert stats["relationships"]["CITES"] == 5

    def test_context_manager(self, mock_settings, mock_driver):
        """Test context manager usage."""
        with Neo4jClient() as client:
            assert client.driver is not None

    def test_error_handling(self, client, mock_driver):
        """Test error handling."""
        driver_mock, session_mock = mock_driver
        
        client.connect()
        
        session_mock.run.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception):
            client.execute_query("MATCH (n) RETURN n")
            
        with pytest.raises(Exception):
            client.execute_write("CREATE (n)")

    def test_not_connected_error(self, client):
        """Test error when not connected."""
        with pytest.raises(RuntimeError):
            client.execute_query("MATCH (n) RETURN n")
            
        with pytest.raises(RuntimeError):
            client.execute_write("CREATE (n)")
