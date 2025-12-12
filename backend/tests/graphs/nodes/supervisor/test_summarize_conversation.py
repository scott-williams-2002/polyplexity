"""
Tests for summarize_conversation node and manage_chat_history reducer.
"""
from unittest.mock import Mock, patch

import pytest

from polyplexity_agent.graphs.nodes.supervisor.summarize_conversation import (
    manage_chat_history,
    summarize_conversation_node,
)


def test_manage_chat_history_append():
    """Test manage_chat_history appends new messages."""
    current = [{"role": "user", "content": "Hello"}]
    new = [{"role": "assistant", "content": "Hi"}]
    
    result = manage_chat_history(current, new)
    
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"


def test_manage_chat_history_reset():
    """Test manage_chat_history handles reset signal."""
    current = [{"role": "user", "content": "Old"}]
    new = [{"type": "reset"}, {"role": "user", "content": "New"}]
    
    result = manage_chat_history(current, new)
    
    assert len(result) == 1
    assert result[0]["content"] == "New"


def test_manage_chat_history_limit():
    """Test manage_chat_history enforces 50 message limit."""
    current = [{"role": "user", "content": f"Message {i}"} for i in range(50)]
    new = [{"role": "assistant", "content": "New message"}]
    
    result = manage_chat_history(current, new)
    
    assert len(result) == 50
    assert result[-1]["content"] == "New message"


@pytest.fixture
def sample_state():
    """Create a sample state with conversation history."""
    return {
        "conversation_history": [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
            {"role": "assistant", "content": "Answer 2"},
        ],
        "conversation_summary": "Previous summary",
    }


@patch("polyplexity_agent.graphs.nodes.supervisor.summarize_conversation.create_llm_model")
def test_summarize_conversation_node(
    mock_create_llm_model,
    sample_state,
):
    """Test summarize_conversation_node generates summary."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Updated summary"
    mock_create_llm_model.return_value = mock_llm
    
    result = summarize_conversation_node(sample_state)
    
    assert "conversation_summary" in result
    assert result["conversation_summary"] == "Updated summary"
    assert "conversation_history" in result
    assert result["conversation_history"][0]["type"] == "reset"


@patch("polyplexity_agent.graphs.nodes.supervisor.summarize_conversation.create_llm_model")
def test_summarize_conversation_node_empty_history(
    mock_create_llm_model,
):
    """Test summarize_conversation_node handles empty history."""
    state = {"conversation_history": []}
    
    result = summarize_conversation_node(state)
    
    assert result == {}


@patch("polyplexity_agent.graphs.nodes.supervisor.summarize_conversation.create_llm_model")
def test_summarize_conversation_node_formats_history(
    mock_create_llm_model,
    sample_state,
):
    """Test summarize_conversation_node formats history correctly."""
    mock_llm = Mock()
    mock_llm.invoke.return_value.content = "Summary"
    mock_create_llm_model.return_value = mock_llm
    
    summarize_conversation_node(sample_state)
    
    # Verify LLM was called with formatted history
    call_args = mock_create_llm_model.return_value.invoke.call_args[0][0]
    assert len(call_args) == 2
    # Check that history was formatted (should contain USER and ASSISTANT)
    prompt_content = call_args[1].content
    assert "USER:" in prompt_content or "ASSISTANT:" in prompt_content
