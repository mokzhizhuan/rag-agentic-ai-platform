"""Shared validation utilities and constants for equipment maintenance scheduling."""

from datetime import date, timedelta
import unittest
from typing import Any, Iterable, Mapping


ISO_DATE_FORMAT = "%Y-%m-%d"
MIN_INTERVAL_DAYS = 1
DATE_TYPE_ERROR = "date must be an ISO YYYY-MM-DD string or a date instance"
INVALID_DATE_ERROR = "date must be a valid ISO YYYY-MM-DD date"
INTERVAL_TYPE_ERROR = "interval_days must be a positive integer"
EQUIPMENT_RECORDS_TYPE_ERROR = "equipment_records must be an iterable of mappings"


def _validate_date(value: Any, field_name: str) -> date:
    """Validate and normalize an ISO date string or date instance."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field_name} {DATE_TYPE_ERROR}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} {INVALID_DATE_ERROR}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field_name} {INVALID_DATE_ERROR}")
    return parsed


def _validate_interval(interval_days: Any) -> int:
    """Validate a positive integer maintenance interval."""
    if isinstance(interval_days, bool) or not isinstance(interval_days, int):
        raise TypeError(INTERVAL_TYPE_ERROR)
    if interval_days < MIN_INTERVAL_DAYS:
        raise ValueError(INTERVAL_TYPE_ERROR)
    return interval_days


def _validate_equipment_records(
    equipment_records: Any,
) -> Iterable[Mapping[str, Any]]:
    """Validate that equipment records are iterable mappings."""
    if isinstance(equipment_records, (str, bytes, Mapping)):
        raise TypeError(EQUIPMENT_RECORDS_TYPE_ERROR)
    try:
        records = iter(equipment_records)
    except TypeError as exc:
        raise TypeError(EQUIPMENT_RECORDS_TYPE_ERROR) from exc
    return records

from datetime import date, datetime
import re

def date_validation(value, field="date", interval=False):
    """Validate an ISO date or positive integer interval."""
    if interval:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{field} must be a positive integer")
        return value
    if isinstance(value, datetime):
        raise TypeError(f"{field} must be a date or YYYY-MM-DD string")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field} must be a valid YYYY-MM-DD date") from exc
    raise TypeError(f"{field} must be a date or YYYY-MM-DD string")

def calculate_next_maintenance(
    last_service_date: Any,
    interval_days: Any,
) -> str:
    """Calculate the next maintenance date as an ISO date string."""
    service_date = _validate_date(last_service_date, "last_service_date")
    interval = _validate_interval(interval_days)
    return (service_date + timedelta(days=interval)).isoformat()

def is_maintenance_overdue(next_service_date: Any, reference_date: Any) -> bool:
    """Return whether maintenance is due on or before the reference date."""
    next_date = _validate_date(next_service_date, "next_service_date")
    reference = _validate_date(reference_date, "reference_date")
    return next_date <= reference

def maintenance_summary(equipment_records: Any, reference_date: Any) -> list[dict[str, Any]]:
    """Return next-service dates and overdue status for each equipment record."""
    reference = _validate_date(reference_date, "reference_date")
    records = _validate_equipment_records(equipment_records)
    summary = []

    for record in records:
        if not isinstance(record, Mapping):
            raise TypeError(EQUIPMENT_RECORDS_TYPE_ERROR)

        if "equipment_id" not in record:
            raise KeyError("equipment_id")
        if "last_service_date" not in record:
            raise KeyError("last_service_date")
        if "interval_days" not in record:
            raise KeyError("interval_days")

        next_service = calculate_next_maintenance(
            record["last_service_date"],
            record["interval_days"],
        )
        overdue = is_maintenance_overdue(next_service, reference)

        if isinstance(next_service, date):
            next_service_value = next_service.isoformat()
        else:
            next_service_value = next_service

        summary.append(
            {
                "equipment_id": record["equipment_id"],
                "next_service_date": next_service_value,
                "overdue": overdue,
            }
        )

    return summary

def sample_entry_point():
    """Print a maintenance summary for representative equipment."""
    records = [
        {
            "equipment_id": "GEN-001",
            "last_service_date": "2024-12-01",
            "interval_days": 30,
        },
        {
            "equipment_id": "PMP-002",
            "last_service_date": "2024-12-20",
            "interval_days": 45,
        },
        {
            "equipment_id": "HVAC-003",
            "last_service_date": "2024-11-15",
            "interval_days": 60,
        },
    ]
    reference_date = "2025-01-01"
    summary = maintenance_summary(records, reference_date)
    print("Equipment maintenance summary")
    print(f"Reference date: {reference_date}")
    for item in summary:
        print(item)


if __name__ == "__main__":
    sample_entry_point()

class TestMaintenanceScheduling(unittest.TestCase):
    def test_normal_scheduling(self):
        self.assertEqual(
            calculate_next_maintenance("2025-01-15", 30),
            "2025-02-14",
        )

    def test_normal_scheduling_with_date_instance(self):
        self.assertEqual(
            calculate_next_maintenance(date(2024, 2, 28), 2),
            "2024-03-01",
        )

    def test_overdue_maintenance(self):
        self.assertTrue(
            is_maintenance_overdue("2025-01-31", "2025-02-01")
        )
        self.assertFalse(
            is_maintenance_overdue("2025-02-01", "2025-02-01")
        )
        self.assertFalse(
            is_maintenance_overdue("2025-02-02", "2025-02-01")
        )

    def test_invalid_dates(self):
        with self.assertRaises(ValueError):
            calculate_next_maintenance("2025-02-30", 10)
        with self.assertRaises(ValueError):
            calculate_next_maintenance("01-15-2025", 10)
        with self.assertRaises(ValueError):
            is_maintenance_overdue("2025-04-31", "2025-05-01")

    def test_invalid_intervals(self):
        with self.assertRaises(ValueError):
            calculate_next_maintenance("2025-01-01", 0)
        with self.assertRaises(ValueError):
            calculate_next_maintenance("2025-01-01", -5)
        with self.assertRaises(TypeError):
            calculate_next_maintenance("2025-01-01", "30")
        with self.assertRaises(TypeError):
            calculate_next_maintenance("2025-01-01", True)

    def test_multiple_equipment_records(self):
        records = [
            {
                "equipment_id": "pump-1",
                "last_service_date": "2025-01-01",
                "interval_days": 30,
            },
            {
                "equipment_id": "generator-2",
                "last_service_date": "2025-02-15",
                "interval_days": 60,
            },
        ]
        summary = maintenance_summary(records, "2025-02-20")

        if isinstance(summary, Mapping):
            entries = list(summary.values())
            if "pump-1" in summary and isinstance(summary["pump-1"], Mapping):
                entries = list(summary.values())
        else:
            entries = list(summary)

        self.assertEqual(len(entries), 2)
        serialized = repr(summary)
        self.assertIn("2025-01-31", serialized)
        self.assertIn("2025-04-16", serialized)
        self.assertIn("pump-1", serialized)
        self.assertIn("generator-2", serialized)

    def test_summary_rejects_invalid_records(self):
        with self.assertRaises(TypeError):
            maintenance_summary("not records", "2025-02-20")

    def test_summary_rejects_invalid_reference_date(self):
        records = [
            {
                "equipment_id": "pump-1",
                "last_service_date": "2025-01-01",
                "interval_days": 30,
            }
        ]
        with self.assertRaises(ValueError):
            maintenance_summary(records, "2025-02-30")
