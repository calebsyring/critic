from datetime import UTC, datetime


def is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def to_utc(dt: datetime) -> datetime:
    if not is_aware(dt):
        raise ValueError(f'datetime must be timezone aware, got {dt}')
    return dt.astimezone(UTC)
