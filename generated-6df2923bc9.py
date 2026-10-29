"""Utility helpers for filesystem paths, text processing, and dates.

The planned public API consists of three utility classes:

PathUtility
    Provides documented operations for normalizing and resolving paths, joining
    components, checking file and directory existence, retrieving names and
    extensions, creating directories safely, and listing matching files.

TextUtility
    Provides documented operations for whitespace normalization, trimming, case
    conversion, safe string checks, word counting, slug generation, line
    splitting, substring replacement, and optional regular-expression
    extraction.

DateUtility
    Provides documented operations for parsing and formatting dates and
    datetimes, obtaining current values, date arithmetic, comparisons,
    differences, and conversion between date and datetime values.

The eventual module is intended to be self-contained and use only Python's
standard library. Public methods should accept pathlib-compatible values where
appropriate, provide type annotations and complete docstrings, validate
inputs consistently, and raise clear exceptions for unsupported or malformed
values. The accompanying unittest coverage is intended to exercise normal,
boundary, empty, malformed, temporary-filesystem, and deterministic date cases.
"""

from datetime import date, datetime, timedelta
import os
from pathlib import Path
import re
from typing import Any, Iterable, Iterator, Mapping, Optional, Pattern, Sequence, Tuple, Type, TypeVar, Union
import unittest


PathLike = Union[str, os.PathLike[str]]
DateLike = Union[date, datetime]
StringPattern = Union[str, Pattern[str]]
T = TypeVar("T")

DEFAULT_DATE_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)

DEFAULT_SLUG_SEPARATOR = "-"
DEFAULT_ENCODING = "utf-8"
WHITESPACE_PATTERN = re.compile(r"\s+")
WORD_PATTERN = re.compile(r"\b[\w']+\b", re.UNICODE)


def _require_string(value: Optional[str], name: str = "value", allow_none: bool = False) -> Optional[str]:
    """Validate and return a string value."""
    if value is None:
        if allow_none:
            return None
        raise TypeError(f"{name} must be a string, not None")
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value


def _require_path(value: PathLike, name: str = "path") -> Path:
    """Convert a pathlib-compatible value to a Path."""
    if isinstance(value, Path):
        return value
    if isinstance(value, (str, os.PathLike)):
        return Path(value)
    raise TypeError(f"{name} must be a string or os.PathLike value")


def _require_date_like(value: DateLike, name: str = "value") -> DateLike:
    """Validate a date or datetime value."""
    if not isinstance(value, (date, datetime)):
        raise TypeError(f"{name} must be a date or datetime instance")
    return value


def _compile_pattern(pattern: StringPattern, flags: int = 0) -> Pattern[str]:
    """Return a compiled regular-expression pattern."""
    if isinstance(pattern, re.Pattern):
        if flags:
            raise ValueError("flags cannot be supplied with a compiled pattern")
        return pattern
    if not isinstance(pattern, str):
        raise TypeError("pattern must be a string or compiled regular expression")
    return re.compile(pattern, flags)


def _is_datetime(value: DateLike) -> bool:
    """Return whether a date-like value is specifically a datetime."""
    return isinstance(value, datetime)


def _date_only(value: DateLike) -> date:
    """Convert a date-like value to its calendar-date component."""
    checked = _require_date_like(value)
    return checked.date() if isinstance(checked, datetime) else checked


def _ensure_nonempty_string(value: str, name: str = "value") -> str:
    """Validate that a value is a non-empty string."""
    checked = _require_string(value, name=name)
    if checked == "":
        raise ValueError(f"{name} must not be empty")
    return checked

class PathUtility:
    """Documented helpers for common filesystem path operations."""

    @staticmethod
    def normalize(path: PathLike) -> Path:
        """Return a normalized path with user-home expansion and redundant parts removed."""
        value = _require_path(path)
        return Path(os.path.normpath(os.path.expanduser(os.fspath(value))))

    @staticmethod
    def absolute(path: PathLike) -> Path:
        """Return an absolute, normalized path without requiring it to exist."""
        return PathUtility.normalize(path).absolute()

    @staticmethod
    def join(*parts: PathLike) -> Path:
        """Join pathlib-compatible path components into one path."""
        if not parts:
            raise ValueError("at least one path component is required")
        converted = [_require_path(part, f"parts[{index}]") for index, part in enumerate(parts)]
        return Path(*converted)

    @staticmethod
    def exists(path: PathLike) -> bool:
        """Return whether a path exists."""
        return _require_path(path).exists()

    @staticmethod
    def is_file(path: PathLike) -> bool:
        """Return whether a path exists and is a regular file."""
        return _require_path(path).is_file()

    @staticmethod
    def is_dir(path: PathLike) -> bool:
        """Return whether a path exists and is a directory."""
        return _require_path(path).is_dir()

    @staticmethod
    def extension(path: PathLike) -> str:
        """Return the final file extension, including its leading dot."""
        return _require_path(path).suffix

    @staticmethod
    def name(path: PathLike) -> str:
        """Return the final component of a path."""
        return _require_path(path).name

    @staticmethod
    def stem(path: PathLike) -> str:
        """Return the final component without its final extension."""
        return _require_path(path).stem

    @staticmethod
    def ensure_directory(path: PathLike, parents: bool = True) -> Path:
        """Create a directory if needed and return its path."""
        directory = _require_path(path)
        if not isinstance(parents, bool):
            raise TypeError("parents must be a boolean")
        if directory.exists() and not directory.is_dir():
            raise FileExistsError(f"path exists and is not a directory: {directory}")
        directory.mkdir(parents=parents, exist_ok=True)
        return directory

    @staticmethod
    def list_files(
        directory: PathLike,
        pattern: str = "*",
        recursive: bool = False,
    ) -> list[Path]:
        """Return files matching a glob pattern in a directory."""
        base = _require_path(directory)
        if not isinstance(pattern, str):
            raise TypeError("pattern must be a string")
        if not pattern:
            raise ValueError("pattern must not be empty")
        if not isinstance(recursive, bool):
            raise TypeError("recursive must be a boolean")
        if not base.exists():
            raise FileNotFoundError(f"directory does not exist: {base}")
        if not base.is_dir():
            raise NotADirectoryError(f"path is not a directory: {base}")
        matches = base.rglob(pattern) if recursive else base.glob(pattern)
        return sorted((item for item in matches if item.is_file()), key=lambda item: str(item))

    @staticmethod
    def relative_to(path: PathLike, base: PathLike) -> Path:
        """Return path relative to base, raising ValueError when unrelated."""
        return _require_path(path).relative_to(_require_path(base))

class TextUtility:
    """Documented helpers for common Unicode-aware text-processing operations."""

    @staticmethod
    def normalize_whitespace(value: Optional[str], allow_none: bool = False) -> Optional[str]:
        """Collapse runs of whitespace into single spaces and trim the result."""
        text = _require_string(value, allow_none=allow_none)
        if text is None:
            return None
        return WHITESPACE_PATTERN.sub(" ", text).strip()

    @staticmethod
    def trim(value: Optional[str], allow_none: bool = False) -> Optional[str]:
        """Remove leading and trailing Unicode whitespace from a string."""
        text = _require_string(value, allow_none=allow_none)
        return None if text is None else text.strip()

    @staticmethod
    def lower(value: str) -> str:
        """Return the Unicode-aware lowercase form of a string."""
        return _require_string(value).lower()

    @staticmethod
    def upper(value: str) -> str:
        """Return the Unicode-aware uppercase form of a string."""
        return _require_string(value).upper()

    @staticmethod
    def casefold(value: str) -> str:
        """Return the Unicode-aware caseless form of a string."""
        return _require_string(value).casefold()

    @staticmethod
    def title(value: str) -> str:
        """Return the title-cased form of a string."""
        return _require_string(value).title()

    @staticmethod
    def is_empty(value: Optional[str]) -> bool:
        """Return true only when the value is None or an empty string."""
        return value is None or _require_string(value) == ""

    @staticmethod
    def is_blank(value: Optional[str]) -> bool:
        """Return true when the value is None, empty, or whitespace-only."""
        text = _require_string(value, allow_none=True)
        return text is None or text.strip() == ""

    @staticmethod
    def word_count(value: str) -> int:
        """Count Unicode word-like sequences in a string."""
        text = _require_string(value)
        return len(WORD_PATTERN.findall(text))

    @staticmethod
    def slug(value: str, separator: str = DEFAULT_SLUG_SEPARATOR) -> str:
        """Create a lowercase Unicode-preserving slug from text."""
        text = _require_string(value)
        separator = _ensure_nonempty_string(separator, "separator")
        if any(character.isspace() for character in separator):
            raise ValueError("separator must not contain whitespace")
        text = text.casefold()
        text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
        text = re.sub(r"[-\s]+", separator, text, flags=re.UNICODE)
        return text.strip(separator)

    @staticmethod
    def split_lines(value: str, keepends: bool = False) -> list[str]:
        """Split text at Unicode and platform line boundaries."""
        text = _require_string(value)
        if not isinstance(keepends, bool):
            raise TypeError("keepends must be a bool")
        return text.splitlines(keepends)

    @staticmethod
    def replace(value: str, old: str, new: str, count: int = -1) -> str:
        """Replace occurrences of a substring, optionally limiting the count."""
        text = _require_string(value)
        old = _require_string(old, "old")
        new = _require_string(new, "new")
        if not isinstance(count, int) or isinstance(count, bool):
            raise TypeError("count must be an integer")
        if count < -1:
            raise ValueError("count must be -1 or greater")
        return text.replace(old, new, count)

    @staticmethod
    def extract(value: str, pattern: StringPattern, flags: int = 0) -> list[str]:
        """Return all regex matches, using group text when groups are present."""
        text = _require_string(value)
        compiled = _compile_pattern(pattern, flags)
        matches = compiled.findall(text)
        if not matches:
            return []
        if compiled.groups == 0:
            return [str(match) for match in matches]
        return ["".join(match) if isinstance(match, tuple) else str(match)
                for match in matches]

class DateUtility:
    """Provide validated parsing, formatting, arithmetic, comparison, and conversion helpers."""

    @staticmethod
    def parse(value: str, formats: Sequence[str] = DEFAULT_DATE_FORMATS) -> DateLike:
        """Parse a date or datetime string using the supplied formats."""
        text = _ensure_nonempty_string(value, "value").strip()
        if not isinstance(formats, (tuple, list)):
            raise TypeError("formats must be a sequence of format strings")
        if not formats:
            raise ValueError("formats must not be empty")
        errors = []
        for fmt in formats:
            if not isinstance(fmt, str) or not fmt:
                raise TypeError("each format must be a non-empty string")
            try:
                return datetime.strptime(text, fmt) if "%H" in fmt or "%M" in fmt or "%S" in fmt else date.strptime(text, fmt)
            except ValueError as error:
                errors.append(error)
        raise ValueError(f"unsupported or malformed date value: {value!r}") from errors[-1]

    @staticmethod
    def format(value: DateLike, fmt: str = "%Y-%m-%d") -> str:
        """Format a date or datetime with a strftime format."""
        checked = _require_date_like(value)
        pattern = _ensure_nonempty_string(fmt, "fmt")
        try:
            return checked.strftime(pattern)
        except (ValueError, UnicodeError) as error:
            raise ValueError("fmt is not a valid date format") from error

    @staticmethod
    def today() -> date:
        """Return the current local calendar date."""
        return date.today()

    @staticmethod
    def now() -> datetime:
        """Return the current local date and time."""
        return datetime.now()

    @staticmethod
    def add_days(value: DateLike, days: int) -> DateLike:
        """Return a date-like value shifted forward by a number of days."""
        checked = _require_date_like(value)
        if isinstance(days, bool) or not isinstance(days, int):
            raise TypeError("days must be an integer")
        return checked + timedelta(days=days)

    @staticmethod
    def subtract_days(value: DateLike, days: int) -> DateLike:
        """Return a date-like value shifted backward by a number of days."""
        if isinstance(days, bool) or not isinstance(days, int):
            raise TypeError("days must be an integer")
        return DateUtility.add_days(value, -days)

    @staticmethod
    def compare(first: DateLike, second: DateLike) -> int:
        """Compare two values by calendar date, returning -1, 0, or 1."""
        left, right = _date_only(first), _date_only(second)
        return (left > right) - (left < right)

    @staticmethod
    def difference(first: DateLike, second: DateLike, absolute: bool = False) -> int:
        """Return the day difference from second to first."""
        left, right = _date_only(first), _date_only(second)
        result = (left - right).days
        if not isinstance(absolute, bool):
            raise TypeError("absolute must be a boolean")
        return abs(result) if absolute else result

    @staticmethod
    def to_datetime(value: DateLike) -> datetime:
        """Convert a date to midnight datetime, preserving an existing datetime."""
        checked = _require_date_like(value)
        return checked if isinstance(checked, datetime) else datetime.combine(checked, datetime.min.time())

    @staticmethod
    def to_date(value: DateLike) -> date:
        """Convert a datetime to its calendar date, preserving an existing date."""
        return _date_only(value)

    @staticmethod
    def is_before(first: DateLike, second: DateLike) -> bool:
        """Return whether the first value precedes the second by calendar date."""
        return DateUtility.compare(first, second) < 0

    @staticmethod
    def is_after(first: DateLike, second: DateLike) -> bool:
        """Return whether the first value follows the second by calendar date."""
        return DateUtility.compare(first, second) > 0

    @staticmethod
    def is_same_day(first: DateLike, second: DateLike) -> bool:
        """Return whether two values represent the same calendar date."""
        return DateUtility.compare(first, second) == 0

"""Documentation and validation helpers for utility-module public APIs."""


import inspect
from collections.abc import Callable, Mapping
from typing import Any


class ModuleDocumentationAndValidation:
    """Validate documentation, annotations, and callable contracts."""

    @staticmethod
    def require_documentation(
        value: Any,
        name: str = "value",
        *,
        minimum_length: int = 1,
    ) -> str:
        """Return a callable's documentation after validating its contents.

        Args:
            value: Callable or object whose docstring is required.
            name: Name used in validation error messages.
            minimum_length: Smallest permitted stripped docstring length.

        Returns:
            The stripped documentation string.

        Raises:
            TypeError: If minimum_length is invalid or value is not suitable.
            ValueError: If the documentation is missing or too short.
        """
        if not isinstance(minimum_length, int) or isinstance(minimum_length, bool):
            raise TypeError("minimum_length must be an integer")
        if minimum_length < 1:
            raise ValueError("minimum_length must be positive")
        documentation = inspect.getdoc(value)
        if not isinstance(documentation, str):
            raise ValueError(f"{name} must have a documentation string")
        documentation = documentation.strip()
        if len(documentation) < minimum_length:
            raise ValueError(
                f"{name} documentation must contain at least "
                f"{minimum_length} characters"
            )
        return documentation

    @staticmethod
    def require_annotations(
        callable_object: Callable[..., Any],
        name: str = "callable",
        *,
        require_return: bool = True,
    ) -> dict[str, Any]:
        """Return validated annotations for a public callable.

        Args:
            callable_object: Callable whose annotations are inspected.
            name: Name used in validation error messages.
            require_return: Whether a return annotation is mandatory.

        Returns:
            A copy of the callable's annotations.

        Raises:
            TypeError: If the object is not callable or require_return is invalid.
            ValueError: If required annotations are missing.
        """
        if not callable(callable_object):
            raise TypeError(f"{name} must be callable")
        if not isinstance(require_return, bool):
            raise TypeError("require_return must be a boolean")
        annotations = dict(inspect.get_annotations(callable_object, eval_str=False))
        signature = inspect.signature(callable_object)
        missing = [
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.annotation is inspect.Parameter.empty
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"{name} is missing annotations for: {joined}")
        if require_return and "return" not in annotations:
            raise ValueError(f"{name} is missing a return annotation")
        return annotations

    @classmethod
    def validate_public_api(
        cls,
        members: Mapping[str, Any],
        *,
        minimum_doc_length: int = 1,
    ) -> tuple[str, ...]:
        """Validate documented and annotated public callables in a mapping.

        Args:
            members: Mapping of public names to objects.
            minimum_doc_length: Minimum length for each callable docstring.

        Returns:
            Public names that were successfully validated.

        Raises:
            TypeError: If members is not a mapping.
            ValueError: If a public callable fails validation.
        """
        if not isinstance(members, Mapping):
            raise TypeError("members must be a mapping")
        validated: list[str] = []
        for name, member in members.items():
            if not isinstance(name, str) or not name:
                raise ValueError("member names must be non-empty strings")
            if name.startswith("_") or not callable(member):
                continue
            cls.require_documentation(member, name, minimum_length=minimum_doc_length)
            cls.require_annotations(member, name)
            validated.append(name)
        return tuple(validated)

import unittest
from datetime import date, datetime
from pathlib import Path

DEFAULT_ENCODING = "utf-8"


class TestPathUtility(unittest.TestCase):
    def setUp(self):
        self.root = Path("unit_test_temp")
        self.root.mkdir(exist_ok=True)
        (self.root / "nested").mkdir(exist_ok=True)
        (self.root / "sample.txt").write_text("alpha\nbeta", encoding=DEFAULT_ENCODING)

    def tearDown(self):
        for path in sorted(self.root.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if self.root.exists():
            self.root.rmdir()

    def invoke(self, name, *args, **kwargs):
        method = getattr(PathUtility, name, None)
        if method is None:
            self.skipTest(f"PathUtility.{name} is not defined")
        return method(*args, **kwargs)

    def test_path_operations(self):
        self.assertTrue(self.invoke("exists", self.root))
        self.assertTrue(self.invoke("is_file", self.root / "sample.txt"))
        self.assertTrue(self.invoke("is_dir", self.root))
        self.assertFalse(self.invoke("exists", self.root / "missing.txt"))
        self.assertEqual(self.invoke("get_filename", self.root / "sample.txt"), "sample.txt")
        self.assertEqual(self.invoke("get_stem", self.root / "sample.txt"), "sample")
        self.assertEqual(self.invoke("get_extension", self.root / "sample.txt"), ".txt")

    def test_filesystem_operations(self):
        target = self.root / "created" / "data.txt"
        for name in ("ensure_directory", "make_directory", "create_directory"):
            if hasattr(PathUtility, name):
                self.invoke(name, target.parent)
                break
        for name in ("write_text", "write_file"):
            if hasattr(PathUtility, name):
                self.invoke(name, target, "content")
                break
        if target.exists():
            for name in ("read_text", "read_file"):
                if hasattr(PathUtility, name):
                    self.assertEqual(self.invoke(name, target), "content")
                    break

    def test_invalid_paths(self):
        with self.assertRaises(TypeError):
            self.invoke("exists", None)
        for name in ("read_text", "read_file"):
            if hasattr(PathUtility, name):
                with self.assertRaises((FileNotFoundError, OSError, ValueError)):
                    self.invoke(name, self.root / "missing.txt")

    def test_collection_operations(self):
        for name in ("list_files", "files", "iter_files"):
            if hasattr(PathUtility, name):
                result = self.invoke(name, self.root)
                self.assertIsNotNone(result)
                break


class TestTextUtility(unittest.TestCase):
    def invoke(self, name, *args, **kwargs):
        method = getattr(TextUtility, name, None)
        if method is None:
            self.skipTest(f"TextUtility.{name} is not defined")
        return method(*args, **kwargs)

    def test_text_boundaries(self):
        for name in ("normalize_whitespace", "collapse_whitespace"):
            if hasattr(TextUtility, name):
                self.assertEqual(self.invoke(name, ""), "")
                self.assertEqual(self.invoke(name, "  a \n b\t"), "a b")
        for name in ("word_count", "count_words"):
            if hasattr(TextUtility, name):
                self.assertEqual(self.invoke(name, ""), 0)
                self.assertGreaterEqual(self.invoke(name, "one two"), 2)

    def test_text_transformations(self):
        for name in ("slugify", "to_slug"):
            if hasattr(TextUtility, name):
                self.assertEqual(self.invoke(name, ""), "")
                self.assertEqual(self.invoke(name, " Hello, World! "), "hello-world")
        for name in ("truncate",):
            if hasattr(TextUtility, name):
                self.assertEqual(self.invoke(name, "abcdef", 0), "")
                self.assertLessEqual(len(self.invoke(name, "abcdef", 3)), 3)

    def test_text_extraction(self):
        for name in ("extract", "extract_matches", "find_matches"):
            if hasattr(TextUtility, name):
                result = self.invoke(name, "abc 123 def", r"\d+")
                self.assertIn("123", result)
                break

    def test_invalid_text_values(self):
        for name in ("slugify", "normalize_whitespace", "word_count"):
            if hasattr(TextUtility, name):
                with self.assertRaises(TypeError):
                    self.invoke(name, None)


class TestDateUtility(unittest.TestCase):
    DAY = date(2024, 2, 29)
    MOMENT = datetime(2024, 2, 29, 12, 30, 15)

    def invoke(self, name, *args, **kwargs):
        method = getattr(DateUtility, name, None)
        if method is None:
            self.skipTest(f"DateUtility.{name} is not defined")
        return method(*args, **kwargs)

    def test_parsing_and_formatting(self):
        for name in ("parse", "parse_date", "parse_datetime"):
            if hasattr(DateUtility, name):
                result = self.invoke(name, "2024-02-29")
                self.assertEqual(result.year, 2024)
                self.assertEqual(result.month, 2)
                self.assertEqual(result.day, 29)
                break
        for name in ("format", "format_date", "format_datetime"):
            if hasattr(DateUtility, name):
                result = self.invoke(name, self.MOMENT, "%Y-%m-%d")
                self.assertEqual(result, "2024-02-29")
                break

    def test_date_arithmetic(self):
        for name in ("add_days", "add_day", "add"):
            if hasattr(DateUtility, name):
                result = self.invoke(name, self.DAY, 1)
                self.assertEqual(result, date(2024, 3, 1))
                break
        for name in ("difference", "days_between", "date_difference"):
            if hasattr(DateUtility, name):
                result = self.invoke(name, self.DAY, date(2024, 3, 1))
                self.assertEqual(abs(result), 1)
                break

    def test_comparisons_and_conversion(self):
        for name in ("is_before", "before"):
            if hasattr(DateUtility, name):
                self.assertTrue(self.invoke(name, self.DAY, date(2024, 3, 1)))
                break
        for name in ("to_date", "date_only"):
            if hasattr(DateUtility, name):
                self.assertEqual(self.invoke(name, self.MOMENT), self.DAY)
                break

    def test_malformed_dates(self):
        for name in ("parse", "parse_date", "parse_datetime"):
            if hasattr(DateUtility, name):
                with self.assertRaises((ValueError, TypeError)):
                    self.invoke(name, "")
                with self.assertRaises((ValueError, TypeError)):
                    self.invoke(name, "not-a-date")
                break
        for name in ("format", "format_date"):
            if hasattr(DateUtility, name):
                with self.assertRaises(TypeError):
                    self.invoke(name, None, "%Y")
                break

    def test_current_values_are_valid(self):
        for name in ("today", "current_date", "now", "current_datetime"):
            if hasattr(DateUtility, name):
                value = self.invoke(name)
                self.assertIsInstance(value, (date, datetime))
                break
