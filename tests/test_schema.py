"""Tests for src.schema."""
import pytest

from src.schema import EnvironmentVariablesNotFoundError


def test_environment_variables_not_found_error_is_exception():
    assert issubclass(EnvironmentVariablesNotFoundError, Exception)


def test_environment_variables_not_found_error_can_be_raised():
    with pytest.raises(EnvironmentVariablesNotFoundError) as exc_info:
        raise EnvironmentVariablesNotFoundError("DISCORD_TOKEN is not set.")
    assert "DISCORD_TOKEN" in str(exc_info.value)


def test_environment_variables_not_found_error_can_be_caught():
    try:
        raise EnvironmentVariablesNotFoundError("CURSOR_API_KEY is not set.")
    except EnvironmentVariablesNotFoundError as e:
        assert "CURSOR_API_KEY" in str(e)
