"""Tests for src.comm_service."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.comm_service import agent_run, client, listen_to_discord, on_message
from src.schema import AgentError, EmptyPromptError, EnvironmentVariablesNotFoundError


def test_listen_to_discord_raises_when_discord_token_missing():
    with patch("src.comm_service.token", ""):
        with patch("src.comm_service.cursor_api_key", "key"):
            with pytest.raises(EnvironmentVariablesNotFoundError) as exc_info:
                listen_to_discord()
            assert "DISCORD" in str(exc_info.value).upper()


def test_listen_to_discord_raises_when_cursor_api_key_missing():
    with patch("src.comm_service.token", "some-token"):
        with patch("src.comm_service.cursor_api_key", ""):
            with pytest.raises(EnvironmentVariablesNotFoundError) as exc_info:
                listen_to_discord()
            assert "CURSOR" in str(exc_info.value).upper() or "API" in str(exc_info.value).upper()


@pytest.mark.asyncio
async def test_agent_run_calls_generate_response_and_add_memory():
    with patch("src.comm_service.generate_response") as mock_gen:
        with patch("src.comm_service.add_memory") as mock_add:
            mock_gen.return_value = "Agent reply"
            result = await agent_run("user prompt")
            assert result == "Agent reply"
            mock_gen.assert_called_once_with("user prompt")
            mock_add.assert_called_once()
            call_arg = mock_add.call_args[0][0]
            assert "user prompt" in call_arg
            assert "Agent reply" in call_arg


@pytest.mark.asyncio
async def test_on_message_ignores_own_messages():
    """on_message should return without calling agent_run when message.author is client.user."""
    mock_message = MagicMock()
    mock_message.author = client.user
    mock_message.content = "hello"
    with patch("src.comm_service.agent_run", new_callable=AsyncMock) as mock_agent:
        await on_message(mock_message)
        mock_agent.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_calls_agent_run_and_sends_reply():
    mock_message = MagicMock()
    mock_message.author = MagicMock()
    mock_message.author.__eq__ = lambda self, other: False  # not client.user
    mock_message.content = "hello"
    mock_message.channel.send = AsyncMock()
    with patch("src.comm_service.agent_run", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = "agent said hi"
        await on_message(mock_message)
        mock_agent.assert_called_once_with("hello")
        mock_message.channel.send.assert_called_once_with("agent said hi")


@pytest.mark.asyncio
async def test_on_message_sends_error_and_does_not_add_memory_on_agent_error():
    """When generate_response raises, on_message sends the error and add_memory is never called."""
    mock_message = MagicMock()
    mock_message.author = MagicMock()
    mock_message.content = "hello"
    mock_message.channel.send = AsyncMock()
    with patch("src.comm_service.generate_response") as mock_gen:
        with patch("src.comm_service.add_memory") as mock_add:
            mock_gen.side_effect = AgentError("Sorry, something went wrong.")
            await on_message(mock_message)
            mock_message.channel.send.assert_called_once_with("Sorry, something went wrong.")
            mock_add.assert_not_called()
