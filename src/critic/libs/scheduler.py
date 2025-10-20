from __future__ import annotations

import concurrent.futures
import time

from critic.libs.store import query_due_monitors, update_monitor
from critic.libs.uptime import check_monitor
from critic.Monitor.MonitorIn import MonitorIn


def _to_monitor_in(d: dict) -> MonitorIn:
    return MonitorIn(**d)


def run_due_once(max_workers: int = 8, table: str | None = None) -> list[dict]:
    due = query_due_monitors(now=int(time.time()), table=table)
    if not due:
        return []

    results: list[dict] = []

    def _run(d: dict) -> dict:
        m = _to_monitor_in(d)
        r = check_monitor(m)
        updated = {
            **d,
            'state': r.state.value,
            'next_due_at': r.next_due_at,
            'last_status_code': r.status_code,
            'last_latency_ms': r.latency_ms,
            'last_checked_at': r.checked_at,
            'last_body_contains': r.body_contains,
            'GSI_PK': 'DUE_MONITOR',
        }
        update_monitor(updated, table=table)
        return updated

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for updated in pool.map(_run, due):
            results.append(updated)

    return results
