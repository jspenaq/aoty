from datetime import date, datetime


def parse_release_date(date_str: str | None) -> date | None:
    """
    Parses a date string in the format "MonthDay,Year" (e.g., "December2,2022")
    into a datetime.date object.

    Args:
        date_str (str | None): The date string to parse.

    Returns:
        datetime.date | None: The parsed date object, or None if parsing fails.
    """
    if not date_str:
        return None
    try:
        # Use %B for full month name, %d for day of month, %Y for year with century
        dt_object = datetime.strptime(date_str, "%B%d,%Y")
        return dt_object.date()
    except ValueError:
        return None
