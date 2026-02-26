import pytest
from unittest.mock import MagicMock, patch
from app.agent.agent import ParticipantAgent
from app.agent.memory import SharedMemory

@pytest.fixture
def mock_get_chat_completion():
    with patch("app.agent.agent.get_chat_completion") as mock:
        yield mock

def test_memory_operations():
    mem = SharedMemory(n_participants=3)
    # Check initial state (it's not empty string, contains headers)
    initial_str = mem.get_context_str()
    assert "【过往总结】" in initial_str
    assert "(暂无)" in initial_str
    
    mem.add_message("Alice", "Hi")
    # get_context_str returns "Alice: Hi" in format
    assert "Alice: Hi" in mem.get_context_str()
    
    mem.add_message("Bob", "Hello")
    mem.add_message("Charlie", "Hey")

def test_agent_initialization():
    persona = {
        "name": "Socrates",
        "bio": "Philosopher",
        "title": "Thinker",
        "theories": ["Method"],
        "stance": "Neutral",
        "system_prompt": "Be wise."
    }
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="Truth")
    assert agent.name == "Socrates"
    # System prompt is taken from persona['system_prompt'] directly
    assert "Be wise." in agent.system_prompt
    assert "Truth" in agent.theme
    assert "Method" in agent.theories

def test_agent_think_listen(mock_get_chat_completion):
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    # Mock response for "listen"
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"action": "listen", "thought": "I should listen", "target": ""}'
    mock_get_chat_completion.return_value = mock_response
    
    thought = agent.think("Context")
    assert thought["action"] == "listen"

def test_agent_think_speak(mock_get_chat_completion):
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    # Mock response for "speak"
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"action": "speak", "thought": "I will speak", "target": "All"}'
    mock_get_chat_completion.return_value = mock_response
    
    thought = agent.think("Context")
    assert thought["action"] == "speak"

def test_agent_speak_stream(mock_get_chat_completion):
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    thought = {"action": "speak", "thought": "T", "target": "All", "previous": "P", "mind": "M", "benefit": "B"}
    
    # Mock stream
    mock_chunk = MagicMock()
    mock_chunk.choices[0].delta.content = "Hello"
    mock_get_chat_completion.return_value = [mock_chunk]
    
    stream = agent.speak(thought, "Context")
    chunks = list(stream)
    assert len(chunks) == 1
    assert chunks[0].choices[0].delta.content == "Hello"

def test_agent_think_error_handling(mock_get_chat_completion):
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    # Mock invalid JSON - utils.get_chat_completion returns None on error
    mock_get_chat_completion.return_value = None
    
    thought = agent.think("Context")
    assert thought is None
