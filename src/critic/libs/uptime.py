# Add timezone to datetime imports later if needed, removing for linting purposes
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from pydantic import BaseModel

from critic.Monitor.MonitorIn import MonitorIn, _State


def _now_utc() -> datetime:
    return datetime.now(UTC)


class CheckResult(BaseModel):
    project_id: str
    id: str
    state: _State
    status_code: int | None = None
    latency_ms: int | None = None
    body_contains: bool | None = None
    checked_at: int
    next_due_at: int


def check_monitor(m: MonitorIn, now: datetime | None = None) -> CheckResult:
    now = now or _now_utc()
    t0 = now
    status: int | None = None
    latency_ms: int | None = None
    contains: bool | None = None
    ok = False

    try:
        with httpx.Client(follow_redirects=True, timeout=m.timeout) as client:
            resp = client.get(str(m.url))
        status = resp.status_code
        latency_ms = int(((_now_utc()) - t0).total_seconds() * 1000)
        ok = True
        if m.assertions and m.assertions.status_code is not None:
            ok = ok and (status == m.assertions.status_code)
        if m.assertions and m.assertions.body_contains:
            contains = m.assertions.body_contains in resp.text
            ok = ok and contains
    except Exception:
        ok = False

    new_state = _State.up if ok else _State.down
    next_due = int((now + timedelta(minutes=m.interval)).timestamp())

    return CheckResult(
        project_id=m.project_id,
        id=str(m.id),
        state=new_state,
        status_code=status,
        latency_ms=latency_ms,
        body_contains=contains,
        checked_at=int(now.timestamp()),
        next_due_at=next_due,
    )
