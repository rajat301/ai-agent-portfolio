# time_tools.py — functions that retrieve real-world date and time information

from datetime import datetime  # datetime class lets us get the current date and time
from zoneinfo import ZoneInfo  # ZoneInfo is Python's built-in timezone database (Python 3.9+)


def get_current_time() -> str:  # return type annotation — this function always returns a string
    """Return the current date and time in Sydney, Australia as a human-readable string."""

    sydney_tz = ZoneInfo("Australia/Sydney")  # create a timezone object for Sydney; handles AEST/AEDT switchover automatically
    now = datetime.now(sydney_tz)  # get the current moment in time, expressed in the Sydney timezone
    return now.strftime("%A, %d %B %Y %I:%M %p %Z")  # format as e.g. "Tuesday, 13 May 2025 03:45 PM AEST"
