"""Tests for src.ai."""
from unittest.mock import patch, MagicMock

import pytest

from src import ai
from src.schema import AgentError, EmptyPromptError


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


def test_generate_response_empty_prompt_raises():
    with pytest.raises(EmptyPromptError) as exc_info:
        ai.generate_response("")
    assert "non-empty" in str(exc_info.value)
    with pytest.raises(EmptyPromptError):
        ai.generate_response("   ")


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
def test_generate_response_failure_raises_agent_error(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="agent failed")
    with pytest.raises(AgentError) as exc_info:
        ai.generate_response("hello")
    assert "error" in str(exc_info.value).lower()
    assert exc_info.value.stderr == "agent failed"
    mock_run.assert_called_once()


@patch("src.ai.subprocess.run")
def test_generate_response_sanitizes_prompt_before_calling_agent(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    ai.generate_response("  user input  ")
    call_args = mock_run.call_args[0][0]
    assert "user input" in call_args
    assert call_args[-1].startswith("--output-format")
