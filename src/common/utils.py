"""Small shared helpers."""
import math


def js_round(x):
    """
    Match JavaScript's Math.round (round half UP), NOT Python's banker's
    rounding. Math.round(2.5)==3 whereas Python round(2.5)==2. Ratings are
    non-negative, so floor(x + 0.5) is sufficient and exact here.
    """
    return int(math.floor(x + 0.5))


def iso_z(dt):
    """
    Format a datetime the way Mongoose/JSON does: ISO-8601 with millisecond
    precision and a trailing 'Z' (e.g. "2024-01-01T00:00:00.000Z").
    Returns None for a falsy value.
    """
    if not dt:
        return None
    # Normalize to UTC without changing the instant.
    from datetime import timezone

    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"
