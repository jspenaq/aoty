import pytest
from datetime import date

from src.aoty.utils import parse_release_date


@pytest.mark.parametrize(
    "date_str, expected_date",
    [
        ("December2,2022", date(2022, 12, 2)),
        ("January1,2000", date(2000, 1, 1)),
        ("February29,2024", date(2024, 2, 29)),  # Leap year
        ("March15,1995", date(1995, 3, 15)),
        ("October31,2023", date(2023, 10, 31)),
        ("November1,2020", date(2020, 11, 1)),
    ],
)
def test_parse_release_date_valid_input(date_str, expected_date):
    """Test parse_release_date with valid date strings."""
    assert parse_release_date(date_str) == expected_date


@pytest.mark.parametrize(
    "date_str",
    [
        "InvalidDate",
        "December 32,2022",  # Invalid day
        "Feb 29,2023",  # Non-leap year
        "December2 2022",  # Missing comma
        "2022,December2",  # Wrong order
        "December 2, 2022",  # Extra space after month
        "December2, 2022",  # Extra space after comma
        "December2,22",  # Two-digit year
        "December2",  # Missing year
        "2,2022",  # Missing month
        "",  # Empty string
    ],
)
def test_parse_release_date_invalid_input(date_str):
    """Test parse_release_date with invalid date strings."""
    assert parse_release_date(date_str) is None


def test_parse_release_date_none_input():
    """Test parse_release_date with None input."""
    assert parse_release_date(None) is None

