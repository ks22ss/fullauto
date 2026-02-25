"""Pytest fixtures and configuration."""
import pytest


@pytest.fixture(autouse=True)
def reset_logger_config():
    """Reset logs module configured state so each test gets fresh logger config."""
    import src.logs as logs_module
    logs_module._configured = False
    yield
    logs_module._configured = False
