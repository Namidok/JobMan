"""
Shared date-filtering logic: keep only postings from the last 24 hours.
Handles the different date formats each source returns.
"""

from datetime import datetime, timezone, timedelta
import re

WINDOW_HOURS = 24


def _parse_relative_time(value: str):
    """Parses LinkedIn-style relative strings like '15 hours ago', '2 days ago',
    '3 weeks ago', 'Just now', 'Yesterday' into an absolute UTC datetime."""
    s = value.strip().lower()
    now = datetime.now(timezone.utc)

    if s in ("just now", "moments ago"):
        return now
    if s == "yesterday":
        return now - timedelta(days=1)

    match = re.match(r"(\d+)\s*(minute|hour|day|week|month|year)s?\s*ago", s)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    unit_to_timedelta = {
        "minute": timedelta(minutes=amount),
        "hour": timedelta(hours=amount),
        "day": timedelta(days=amount),
        "week": timedelta(weeks=amount),
        "month": timedelta(days=amount * 30),
        "year": timedelta(days=amount * 365),
    }
    delta = unit_to_timedelta.get(unit)
    if delta is None:
        return None
    return now - delta


def _parse_any_date(value):
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OSError):
            return None

    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d{10}", s):
            return datetime.fromtimestamp(int(s), tz=timezone.utc)
        if re.fullmatch(r"\d{13}", s):
            return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)

        relative = _parse_relative_time(s)
        if relative is not None:
            return relative

        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(s, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    return None


def is_within_last_24h(date_posted_value):
    parsed = _parse_any_date(date_posted_value)
    if parsed is None:
        return False
    now = datetime.now(timezone.utc)
    return now - timedelta(hours=WINDOW_HOURS) <= parsed <= now + timedelta(hours=1)


def filter_last_24h(postings, date_field="date_posted"):
    kept = []
    dropped_unparseable = 0
    for p in postings:
        if is_within_last_24h(p.get(date_field)):
            kept.append(p)
        else:
            dropped_unparseable += 1
    return kept, dropped_unparseable