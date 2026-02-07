from datetime import UTC, datetime, timedelta


def is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def to_utc(dt: datetime) -> datetime:
    if not is_aware(dt):
        raise ValueError(f'datetime must be timezone aware, got {dt}')
    return dt.astimezone(UTC)


def round_minute(dt: datetime) -> datetime:
    # Most of the time we want to round down (that usually means we're erring on the side of
    # running a monitor too often vs. not enough). However, if we're very late in the minute, it's
    # more likely that the task ran just a bit too early and we should round up.
    if dt.second >= 55:
        return dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return dt.replace(second=0, microsecond=0)
