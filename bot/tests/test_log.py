"""Tests for bot/log.py — colored logging formatter."""

import logging
import re

import pytest

from bot.log import ColoredFormatter, parse_log_level

ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


def make_record(level: int, msg: str = "test message") -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=level, pathname="", lineno=0,
        msg=msg, args=(), exc_info=None,
    )


class TestColoredFormatter:
    def setup_method(self):
        self.fmt = ColoredFormatter()

    def test_output_includes_timestamp(self):
        output = self.fmt.format(make_record(logging.INFO))
        assert TIMESTAMP_RE.search(output), f"No timestamp found in: {output!r}"

    def test_output_includes_message(self):
        output = self.fmt.format(make_record(logging.INFO, "hello world"))
        assert "hello world" in output

    def test_output_includes_level_name(self):
        output = self.fmt.format(make_record(logging.ERROR))
        assert "ERROR" in output

    def test_error_is_colored_red(self):
        output = self.fmt.format(make_record(logging.ERROR))
        assert "\x1b[31m" in output, f"Expected red ANSI in ERROR output: {output!r}"

    def test_warning_is_colored_yellow(self):
        output = self.fmt.format(make_record(logging.WARNING))
        assert "\x1b[33m" in output, f"Expected yellow ANSI in WARNING output: {output!r}"

    def test_info_has_no_color(self):
        output = self.fmt.format(make_record(logging.INFO))
        assert not ANSI_ESCAPE.search(output), f"Unexpected ANSI codes in INFO output: {output!r}"

    def test_color_is_reset_after_level(self):
        # Any colored record must end with a reset so the terminal isn't left colored
        for level in (logging.ERROR, logging.WARNING):
            output = self.fmt.format(make_record(level))
            assert output.endswith("\x1b[0m"), f"No reset at end of level {level} output: {output!r}"


class TestParseLogLevel:
    def test_info(self):
        assert parse_log_level("INFO") == logging.INFO

    def test_debug(self):
        assert parse_log_level("DEBUG") == logging.DEBUG

    def test_warning(self):
        assert parse_log_level("WARNING") == logging.WARNING

    def test_case_insensitive(self):
        assert parse_log_level("debug") == logging.DEBUG
        assert parse_log_level("Warning") == logging.WARNING

    def test_invalid_falls_back_to_info(self):
        assert parse_log_level("VERBOSE") == logging.INFO
        assert parse_log_level("") == logging.INFO
