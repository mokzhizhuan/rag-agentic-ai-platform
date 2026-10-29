"""Standalone standard-library utility module for safe path handling, text processing,
ISO date operations, and their corresponding unit tests.

The public utility classes and test cases are intentionally defined separately from
the shared constants and validation helpers below.
"""

from datetime import date, datetime
from pathlib import PurePath
import re
from typing import Any, Optional, Union
import unittest


_EMPTY_STRING_MESSAGE = "value must not be empty"
_STRING_TYPE_MESSAGE = "value must be a string"
_NONNEGATIVE_INTEGER_MESSAGE = "value must be a non-negative integer"
_WHITESPACE_RE = re.compile(r"\s+")
_INVALID_FILENAME_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PATH_SEPARATOR_RE = re.compile(r"[\\/]+")
_DATE_FORMAT = "%Y-%m-%d"
_DATE_SEPARATOR = "-"


def _require_string(value: Any, name: str = "value", *, allow_empty: bool = False) -> str:
    """Validate and return a string argument."""
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not allow_empty and not value:
        raise ValueError(f"{name} must not be empty")
    return value


def _require_nonnegative_integer(value: Any, name: str = "value") -> int:
    """Validate and return a non-negative integer argument."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be a non-negative integer")
    if value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _normalize_whitespace(value: str) -> str:
    """Collapse runs of whitespace and strip surrounding whitespace."""
    return _WHITESPACE_RE.sub(" ", value).strip()


def _is_date_instance(value: Any) -> bool:
    """Return whether a value is a date but not a datetime instance."""
    return isinstance(value, date) and not isinstance(value, datetime)


def _coerce_pure_path(value: str) -> PurePath:
    """Create a platform-independent pure path from a validated string."""
    return PurePath(_PATH_SEPARATOR_RE.sub("/", value))

class PathUtility:
    """Helpers for safe, platform-independent path and filename handling."""

    @staticmethod
    def normalize_path(value: str) -> str:
        """Normalize a relative path without accessing the filesystem."""
        value = _require_string(value, "path")
        if "\x00" in value:
            raise ValueError("path must not contain null characters")
        value = _PATH_SEPARATOR_RE.sub("/", value.strip())
        if not value:
            raise ValueError("path must not be empty")
        if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
            raise ValueError("path must be relative")
        parts = []
        for part in value.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                raise ValueError("path must not contain parent traversal")
            parts.append(part)
        if not parts:
            raise ValueError("path must not resolve to an empty value")
        return "/".join(parts)

    @staticmethod
    def sanitize_filename(value: str, replacement: str = "_") -> str:
        """Return a safe filename with invalid characters replaced."""
        value = _require_string(value, "filename")
        replacement = _require_string(replacement, "replacement")
        if "/" in replacement or "\\" in replacement or "\x00" in replacement:
            raise ValueError("replacement must not contain path separators or null characters")
        value = _INVALID_FILENAME_CHARS_RE.sub(replacement, value)
        value = _normalize_whitespace(value).strip(" .")
        if not value:
            raise ValueError("filename must contain at least one usable character")
        if value in {".", ".."}:
            raise ValueError("filename must not be a traversal component")
        stem = value.split(".", 1)[0].upper()
        if stem in {"CON", "PRN", "AUX", "NUL"} or (
            stem.startswith(("COM", "LPT")) and stem[3:].isdigit()
        ):
            value = f"{replacement}{value}"
        return value

    @staticmethod
    def get_extension(value: str) -> str:
        """Return the final filename extension, including its leading dot."""
        value = _require_string(value, "path")
        if "\x00" in value:
            raise ValueError("path must not contain null characters")
        normalized = PathUtility.normalize_path(value)
        filename = normalized.rsplit("/", 1)[-1]
        if filename in {".", ".."} or filename.startswith(".") and filename.count(".") == 1:
            return ""
        suffix = PurePath(filename).suffix
        return suffix if suffix and suffix != "." else ""

class TextUtility:
    """Utilities for normalizing, counting, and safely truncating text."""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse consecutive whitespace and remove surrounding whitespace."""
        return _normalize_whitespace(_require_string(text, "text", allow_empty=True))

    @staticmethod
    def count_words(text: str) -> int:
        """Count word-like sequences while ignoring standalone punctuation."""
        text = _require_string(text, "text", allow_empty=True)
        if not text:
            return 0
        return len(re.findall(r"\b[\w]+(?:['’\-][\w]+)*\b", text, re.UNICODE))

    @staticmethod
    def truncate(text: str, max_length: int, suffix: str = "") -> str:
        """Truncate text to a maximum length, appending an optional suffix."""
        text = _require_string(text, "text", allow_empty=True)
        max_length = _require_nonnegative_integer(max_length, "max_length")
        suffix = _require_string(suffix, "suffix", allow_empty=True)

        if len(text) <= max_length:
            return text
        if max_length == 0:
            return ""
        if len(suffix) >= max_length:
            return suffix[:max_length]
        return text[:max_length - len(suffix)] + suffix.builder一本道高清无码

class DateUtility:
    """Utilities for parsing, formatting, and comparing calendar dates."""

    @staticmethod
    def parse_iso_date(value: str) -> date:
        """Parse a strictly formatted ISO date in YYYY-MM-DD form."""
        if not isinstance(value, str):
            raise TypeError("value must be an ISO date string")
        if not value:
            raise ValueError("value must not be empty")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError(
                f"invalid ISO date {value!r}; expected format YYYY-MM-DD"
            )
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid calendar date {value!r}") from exc

    @staticmethod
    def _coerce_date(value: Union[str, date], name: str) -> date:
        """Convert a supported date value to a date instance."""
        if isinstance(value, datetime):
            raise TypeError(f"{name} must be a date or ISO date string, not datetime")
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return DateUtility.parse_iso_date(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{name} is not a valid ISO date: {value!r}") from exc
        raise TypeError(f"{name} must be a date or ISO date string")

    @staticmethod
    def format_date(
        value: Union[str, date],
        output_format: str = _DATE_FORMAT,
    ) -> str:
        """Format a date using ISO format by default or a caller-selected format."""
        parsed = DateUtility._coerce_date(value, "value")
        if not isinstance(output_format, str):
            raise TypeError("output_format must be a string")
        if not output_format:
            raise ValueError("output_format must not be empty")
        try:
            return parsed.strftime(output_format)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"unsupported date format string {output_format!r}"
            ) from exc

    @staticmethod
    def difference_days(
        start: Union[str, date],
        end: Union[str, date],
        *,
        absolute: bool = False,
    ) -> int:
        """Return end minus start in days, optionally as a non-negative value."""
        if not isinstance(absolute, bool):
            raise TypeError("absolute must be a boolean")
        start_date = DateUtility._coerce_date(start, "start")
        end_date = DateUtility._coerce_date(end, "end")
        difference = (end_date - start_date).days
        return abs(difference) if absolute else difference

    @staticmethod
    def date_difference(
        first: Union[str, date],
        second: Union[str, date],
        *,
        absolute: bool = False,
    ) -> int:
        """Return the signed or absolute day difference from first to second."""
        return DateUtility.difference_days(first, second, absolute=absolute)

class TestPathUtility(unittest.TestCase):
    def test_normalize_path(self):
        self.assertEqual(PathUtility.normalize_path("a//b/../c"), "a/c")
        self.assertEqual(PathUtility.normalize_path(r"folder\file.txt"), "folder/file.txt")

    def test_normalize_path_edge_cases(self):
        self.assertEqual(PathUtility.normalize_path(""), ".")
        with self.assertRaises(TypeError):
            PathUtility.normalize_path(None)
        with self.assertRaises(ValueError):
            PathUtility.normalize_path("../secret")
        with self.assertRaises(ValueError):
            PathUtility.normalize_path("/absolute/path")

    def test_sanitize_filename(self):
        self.assertEqual(PathUtility.sanitize_filename("report<>:\"/\\|?*.txt"), "report.txt")
        self.assertEqual(PathUtility.sanitize_filename("  report  .txt  "), "report .txt")
        self.assertEqual(PathUtility.sanitize_filename("normal-name_01.txt"), "normal-name_01.txt")

    def test_sanitize_filename_edge_cases(self):
        with self.assertRaises(TypeError):
            PathUtility.sanitize_filename(123)
        with self.assertRaises(ValueError):
            PathUtility.sanitize_filename("")
        with self.assertRaises(ValueError):
            PathUtility.sanitize_filename("   ")
        with self.assertRaises(ValueError):
            PathUtility.sanitize_filename("../secret")
        self.assertEqual(PathUtility.sanitize_filename("archive.tar.gz"), "archive.tar.gz")

    def test_get_extension(self):
        self.assertEqual(PathUtility.get_extension("archive.tar.gz"), ".gz")
        self.assertEqual(PathUtility.get_extension("README"), "")
        self.assertEqual(PathUtility.get_extension(".config"), "")

    def test_get_extension_edge_cases(self):
        with self.assertRaises(TypeError):
            PathUtility.get_extension(None)
        with self.assertRaises(ValueError):
            PathUtility.get_extension("")
        self.assertEqual(PathUtility.get_extension("name."), "")


class TestTextUtility(unittest.TestCase):
    def test_normalize_whitespace(self):
        self.assertEqual(TextUtility.normalize_whitespace("  hello\tworld\nagain  "), "hello world again")
        self.assertEqual(TextUtility.normalize_whitespace(" \t\n "), "")

    def test_normalize_whitespace_invalid_type(self):
        with self.assertRaises(TypeError):
            TextUtility.normalize_whitespace(None)

    def test_count_words(self):
        self.assertEqual(TextUtility.count_words("one two\tthree"), 3)
        self.assertEqual(TextUtility.count_words(""), 0)
        self.assertEqual(TextUtility.count_words(" \n\t "), 0)

    def test_count_words_invalid_type(self):
        with self.assertRaises(TypeError):
            TextUtility.count_words(42)

    def test_truncate(self):
        self.assertEqual(TextUtility.truncate("hello world", 5), "he...")
        self.assertEqual(TextUtility.truncate("hello", 5), "hello")
        self.assertEqual(TextUtility.truncate("hello", 0), "")
        self.assertEqual(TextUtility.truncate("hello", 3, suffix=""), "hel")

    def test_truncate_edge_cases(self):
        with self.assertRaises(TypeError):
            TextUtility.truncate(None, 3)
        with self.assertRaises(TypeError):
            TextUtility.truncate("text", True)
        with self.assertRaises(ValueError):
            TextUtility.truncate("text", -1)
        with self.assertRaises(ValueError):
            TextUtility.truncate("text", 2, suffix="...")


class TestDateUtility(unittest.TestCase):
    def test_parse_and_format_iso_dates(self):
        parsed = DateUtility.parse_iso_date("2024-02-29")
        self.assertEqual(parsed, date(2024, 2, 29))
        self.assertEqual(DateUtility.format_iso_date(parsed), "2024-02-29")

    def test_malformed_and_invalid_dates(self):
        for value in ("", "2024/01/01", "2024-2-1", "not-a-date", "2023-02-29"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    DateUtility.parse_iso_date(value)
        with self.assertRaises(TypeError):
            DateUtility.parse_iso_date(None)
        with self.assertRaises(TypeError):
            DateUtility.format_iso_date("2024-01-01")

    def test_date_differences(self):
        self.assertEqual(
            DateUtility.date_difference("2024-01-01", "2024-01-10"), 9
        )
        self.assertEqual(
            DateUtility.date_difference("2024-01-10", "2024-01-01"), -9
        )
        self.assertEqual(
            DateUtility.date_difference("2024-01-01", "2024-01-01"), 0
        )

    def test_date_difference_invalid_types(self):
        with self.assertRaises(TypeError):
            DateUtility.date_difference(None, "2024-01-01")
        with self.assertRaises(ValueError):
            DateUtility.date_difference("2024-02-30", "2024-03-01")


if __name__ == '__main__':
    unittest.main()
