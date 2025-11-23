import io
import logging
import importlib
import sys

import pytest

import src.core.logs as logs_mod


pytestmark = pytest.mark.unit


def test_logger_is_configured():
    assert hasattr(logs_mod, "logger")
    assert isinstance(logs_mod.logger, logging.Logger)


def test_logs_wrap_non_utf8_stdout(monkeypatch):
    class FakeStdout:
        def __init__(self) -> None:
            self.encoding = "latin-1"
            self.buffer = io.BytesIO()

        def write(self, _s):
            return 0

        def flush(self):
            return None

    monkeypatch.setattr(sys, "stdout", FakeStdout())

    reloaded = importlib.reload(logs_mod)

    assert hasattr(reloaded, "logger")
    assert isinstance(reloaded.logger, logging.Logger)


def test_logs_handles_stdout_buffer_errors(monkeypatch):
    class FakeStdoutBroken:
        def __init__(self) -> None:
            self.encoding = "latin-1"

        @property
        def buffer(self):
            raise RuntimeError("no buffer")

        def write(self, _s):
            return 0

        def flush(self):
            return None

    monkeypatch.setattr(sys, "stdout", FakeStdoutBroken())

    reloaded = importlib.reload(logs_mod)

    assert hasattr(reloaded, "logger")
    assert isinstance(reloaded.logger, logging.Logger)
