import sys
from unittest.mock import MagicMock

mock_agents = MagicMock()

def function_tool(func):
    """Pass-through decorator."""
    return func

mock_agents.function_tool = function_tool
mock_agents.Agent = MagicMock()
mock_agents.Runner = MagicMock()
mock_agents.ModelSettings = MagicMock()

sys.modules["agents"] = mock_agents
