"""Tests for src.logs."""
import logging

import pytest

from src.logs import ROOT_LOGGER_NAME, get_logger, set_level


def test_get_logger_returns_logger():
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)


def test_get_logger_name_includes_root():
    logger = get_logger("test_module")
    assert logger.name == f"{ROOT_LOGGER_NAME}.test_module"


def test_get_logger_same_name_returns_same_instance():
    a = get_logger("foo")
    b = get_logger("foo")
    assert a is b


def test_set_level_accepts_string():
    set_level("DEBUG")
    root = logging.getLogger(ROOT_LOGGER_NAME)
    assert root.level == logging.DEBUG
    set_level("INFO")
    assert root.level == logging.INFO


def test_set_level_accepts_int():
    set_level(logging.WARNING)
    root = logging.getLogger(ROOT_LOGGER_NAME)
    assert root.level == logging.WARNING
    set_level(logging.INFO)
