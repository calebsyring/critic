from datetime import UTC, datetime
import logging

import mu

from critic.libs.dt import round_minute
from critic.libs.uptime import MonitorNotFoundError, UptimeCheck
from critic.tables import UptimeMonitorTable


log = logging.getLogger(__name__)


@mu.task
def run_checks(monitor_id: str, monitor_slug: str):
    try:
        UptimeCheck(monitor_id, monitor_slug).run()
    except MonitorNotFoundError:
        log.info(f'Monitor {monitor_id}/{monitor_slug} not found, skipping')


@mu.task
def run_due_checks():
    """
    This task is invoked by an EventBridge rule once a minute. It queries for all monitors that are
    due and invokes `run_checks` for each one.
    """
    now = datetime.now(UTC)
    log.info(f'Triggering due checks at {now.isoformat()}')

    # Trigger `run_checks` for each due monitor.
    rounded_now = round_minute(now)
    due_monitors = UptimeMonitorTable.get_due_since(rounded_now)
    for monitor in due_monitors:
        run_checks.invoke(str(monitor.project_id), monitor.slug)

    log.info(f'Due checks triggered for {len(due_monitors)} monitors in {datetime.now(UTC) - now}')
