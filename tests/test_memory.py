"""Tests for persistqueue-backed memory."""

from pathlib import Path
from unittest.mock import patch

import persistqueue
import pytest

import src.memory as memory


@pytest.fixture(autouse=True)
def clean_queue(tmp_path, monkeypatch):
    # Redirect queue dir to temp for tests
    qdir = tmp_path / ".fullauto_memory"
    qdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(memory, "QUEUE_DIR", qdir)
    memory.queue = persistqueue.Queue(str(qdir))
    yield
    # cleanup: remove files


def test_add_and_count():
    memory.add_memory("one")
    memory.add_memory("two")
    assert memory.get_message_count() == 2


@patch("src.memory.generate_response")
def test_summarize_when_over_limit(mock_gen):
    mock_gen.return_value = "summary text"
    for i in range(memory.MAX_MESSAGES_BEFORE_SUMMARY + 1):
        memory.add_memory(f"msg {i}")
    assert memory.get_message_count() == 1
    mock_gen.assert_called_once()


@patch("src.memory.generate_response")
def test_summarize_empty_keeps_last_five(mock_gen):
    mock_gen.return_value = ""
    limit = memory.MAX_MESSAGES_BEFORE_SUMMARY
    for i in range(limit + 1):
        memory.add_memory(f"msg {i}")
    assert memory.get_message_count() == limit
