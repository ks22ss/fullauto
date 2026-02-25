"""Tests for src.memory."""
import json
import os
from unittest.mock import patch

import pytest

from src import memory


@pytest.fixture
def temp_memory_file(tmp_path):
    """Point memory module at a temp file so we don't touch real memory.json."""
    path = tmp_path / "memory.json"
    with patch.object(memory, "memory_file", str(path)):
        yield path


def test_load_messages_missing_file_returns_empty(temp_memory_file):
    assert not os.path.isfile(temp_memory_file)
    assert memory._load_messages() == []


def test_load_messages_valid_file_returns_messages(temp_memory_file):
    temp_memory_file.write_text(json.dumps({"messages": ["a", "b"]}, indent=2), encoding="utf-8")
    assert memory._load_messages() == ["a", "b"]


def test_save_messages_writes_valid_json(temp_memory_file):
    memory._save_messages(["one", "two"])
    data = json.loads(temp_memory_file.read_text(encoding="utf-8"))
    assert data == {"messages": ["one", "two"]}


def test_add_memory_appends_and_saves(temp_memory_file):
    memory.add_memory("first")
    assert memory._load_messages() == ["first"]
    memory.add_memory("second")
    assert memory._load_messages() == ["first", "second"]


def test_add_memory_strips_whitespace(temp_memory_file):
    memory.add_memory("  trimmed  ")
    assert memory._load_messages() == ["trimmed"]


def test_get_message_count(temp_memory_file):
    assert memory.get_message_count() == 0
    memory.add_memory("one")
    assert memory.get_message_count() == 1
    memory.add_memory("two")
    assert memory.get_message_count() == 2


@patch.object(memory, "generate_response")
def test_add_memory_when_over_five_summarizes_and_replaces(mock_generate, temp_memory_file):
    mock_generate.return_value = "Summary of everything."
    for i in range(6):
        memory.add_memory(f"message {i}")
    messages = memory._load_messages()
    assert len(messages) == 1
    assert messages[0] == "Summary of everything."
    mock_generate.assert_called_once()


@patch.object(memory, "generate_response")
def test_add_memory_when_over_five_but_summary_empty_keeps_last_five(mock_generate, temp_memory_file):
    mock_generate.return_value = ""
    for i in range(6):
        memory.add_memory(f"message {i}")
    messages = memory._load_messages()
    assert len(messages) == 5
    assert messages[0] == "message 1"
    assert messages[-1] == "message 5"


def test_add_memory_five_or_less_does_not_summarize(temp_memory_file):
    with patch.object(memory, "generate_response") as mock_generate:
        for i in range(5):
            memory.add_memory(f"message {i}")
        mock_generate.assert_not_called()
        assert memory.get_message_count() == 5
