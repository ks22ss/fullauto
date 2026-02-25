"""Tests for src.ai."""
from unittest.mock import patch, MagicMock

import pytest

from src import ai


def test_sanitize_prompt_empty_returns_empty():
    assert ai._sanitize_prompt("") == ""
    assert ai._sanitize_prompt("   ") == ""


def test_sanitize_prompt_strips_whitespace():
    assert ai._sanitize_prompt("  hello  ") == "hello"


def test_sanitize_prompt_removes_control_characters():
    assert "\x00" not in ai._sanitize_prompt("hi\x00there")
    assert "\x1f" not in ai._sanitize_prompt("hi\x1fthere")
    assert ai._sanitize_prompt("hello\x00\x07world") == "helloworld"


def test_sanitize_prompt_preserves_normal_text():
    text = "Hello, world! 你好"
    assert ai._sanitize_prompt(text) == text


def test_generate_response_empty_prompt_returns_please_send_message():
    assert ai.generate_response("") == "Please send a non-empty message."
    assert ai.generate_response("   ") == "Please send a non-empty message."


@patch("src.ai.subprocess.run")
def test_generate_response_success_returns_stdout(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Agent says hi", stderr="")
    assert ai.generate_response("hello") == "Agent says hi"
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert call_args[0] == "agent"
    assert "-p" in call_args
    assert "--force" in call_args
    assert "hello" in call_args


@patch("src.ai.subprocess.run")
def test_generate_response_failure_returns_error_message(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="agent failed")
    assert ai.generate_response("hello") == "Sorry, I encountered an error. Please try again later."
    mock_run.assert_called_once()


@patch("src.ai.subprocess.run")
def test_generate_response_sanitizes_prompt_before_calling_agent(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    ai.generate_response("  user input  ")
    call_args = mock_run.call_args[0][0]
    assert call_args[-1] == "user input"
