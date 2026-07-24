import pytest
from unittest.mock import MagicMock
from orchestrator import JarvisOrchestrator
from router import AgentRouter, AgentProfile

def test_duplicate_call_guard_and_memory_turn():
    mock_router = MagicMock(spec=AgentRouter)
    mock_router.default = AgentProfile.GEMINI
    mock_router.backends = {AgentProfile.GEMINI: MagicMock()}
    
    # Simulate LLM returning tool call 3 times in a row
    mock_router.run.side_effect = [
        '```tool_call\n{"tool": "clipboard_read", "args": {}}\n```',
        '```tool_call\n{"tool": "clipboard_read", "args": {}}\n```',
        '```tool_call\n{"tool": "clipboard_read", "args": {}}\n```',
        'Here is the analysis of the clipboard content: It contains test data.',
    ]
    
    orchestrator = JarvisOrchestrator(router=mock_router, use_vector_memory=False)
    
    # Run orchestrator chat
    response = orchestrator.chat("Test Clipboard Data, analise the data")
    
    # Verify final response is the synthesized answer, NOT the generic duplicate error break string
    assert "analysis of the clipboard content" in response
    
    # Verify working memory recorded assistant turns for tool calls even when clean response was empty
    history = orchestrator.working_memory.get()
    assistant_turns = [m for m in history if m["role"] == "assistant"]
    assert len(assistant_turns) >= 3
    assert "[Executed Tool: clipboard_read({})]" in assistant_turns[0]["content"]
