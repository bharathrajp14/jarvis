import pytest
from pathlib import Path
from actions.galaxy import build_galaxy_graph, query_galaxy
from tools.recall_tools import tool_remember_that
from core.personality import get_boot_briefing

def test_galaxy_graph_build():
    graph = build_galaxy_graph()
    assert "nodes" in graph
    assert "links" in graph
    assert len(graph["nodes"]) > 0

def test_remember_that_tool():
    res = tool_remember_that("prompt packs make excellent free gifts")
    assert "Very good, sir" in res or "indexed" in res

def test_boot_briefing():
    greeting = get_boot_briefing()
    assert "sir" in greeting
    assert "nodes indexed" in greeting
