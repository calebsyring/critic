from datetime import UTC, datetime, timedelta
import logging

import mu

from critic.tables import UptimeMonitorTable


log = logging.getLogger(__name__)


@mu.task
def run_check(project_id: str, slug: str):
    pass


@mu.task
def run_due_checks():
    """
    This task is invoked by an EventBridge rule once a minute. It queries for all monitors that are
    due and invokes `run_check` for each one.
    """
    now = datetime.now(UTC)
    log.info(f'Triggering due checks at {now.isoformat()}')

    # Round `now` to the nearest minute in case there is a slight inaccuracy in scheduling
    rounded_now = now.replace(second=0, microsecond=0)
    if now.second >= 30:
        rounded_now = rounded_now + timedelta(minutes=1)

    # Trigger `run_check` for each due monitor.
    due_monitors = UptimeMonitorTable.get_due_since(rounded_now)
    for monitor in due_monitors:
        run_check.invoke(str(monitor.project_id), monitor.slug)

    log.info(f'Due checks triggered for {len(due_monitors)} monitors in {datetime.now(UTC) - now}')
