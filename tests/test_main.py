"""Tests for src.main (Typer CLI)."""
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from src.main import app

runner = CliRunner()


def test_discord_client_invokes_listen_to_discord():
    with patch("src.main.listen_to_discord") as mock_listen:
        result = runner.invoke(app, ["discord-client"])
        mock_listen.assert_called_once()
        assert result.exit_code == 0


def test_job_runner_invokes_agent_run():
    with patch("src.main.agent_run", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = "done"
        result = runner.invoke(app, ["job-runner"])
        mock_agent.assert_called_once()
        assert "TBC" in str(mock_agent.call_args[0][0])
        assert result.exit_code == 0
