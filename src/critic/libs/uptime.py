from datetime import UTC, datetime, timedelta
from functools import cached_property
import logging
import time

import httpx

from critic.libs.dt import round_minute
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel
from critic.tables import UptimeLogTable, UptimeMonitorTable


log = logging.getLogger(__name__)


class UptimeCheck:
    """
    This class is responsible for running a single uptime check for a given monitor. It handles
    making the request, checking the response, updating the monitor, and saving a log.
    """

    def __init__(self, project_id: str, monitor_slug: str):
        self.now = datetime.now(UTC)
        self.project_id = project_id
        self.monitor_slug = monitor_slug
        # This can technically return None, but we check for that in `run`
        self.monitor: UptimeMonitorModel = UptimeMonitorTable.get(
            self.project_id, self.monitor_slug
        )

        # Used internally to make sure we don't duplicate DB operations
        self._updated_monitor = False
        self._put_log = False

    @cached_property
    def new_next_due_at(self):
        """Returns what the monitor's next due time should be updated to."""
        # Normally we just add the frequency to the last due time. (Not using now helps prevent
        # drift.)
        next_due_at = self.monitor.next_due_at + timedelta(minutes=self.monitor.frequency_mins)

        # If we do that and the next due time is still less than right now, that indicates we're
        # way behind on checks on this monitor, and we need to "reset" relative to now.
        if next_due_at < self.now:
            next_due_at = round_minute(self.now) + timedelta(minutes=self.monitor.frequency_mins)

        return next_due_at

    def update_monitor(self, updates: dict | None = None):
        """
        Updates the monitor with the given updates and also updates the next due time. This method
        should only be called once per monitor check. Only allows the update
        """
        if self._updated_monitor:
            raise Exception(
                'Monitor already updated! Do not call this method more than once in one run.'
            )
        if updates is None:
            updates = {}
        UptimeMonitorTable.update(
            self.project_id,
            self.monitor_slug,
            updates={**updates, 'next_due_at': self.new_next_due_at},
            # Atomic check to make sure we don't update if the monitor was updated since we started
            # TODO: Do we really need this? If so, we need the same for the log I think.
            condition={'next_due_at': self.monitor.next_due_at},
        )
        self._updated_monitor = True

    def make_req(self) -> tuple[httpx.Response | None, float]:
        """
        Makes the request and returns the response and the time it took to make the request.
        """
        start = time.perf_counter()
        with httpx.Client() as client:
            try:
                response = client.head(
                    str(self.monitor.url), timeout=float(self.monitor.timeout_secs)
                )
            except httpx.TimeoutException:
                response = None
        finished = time.perf_counter()
        latency = finished - start
        return response, latency

    def alert(self):
        """TODO: alert self.monitor.alert_slack_channels and self.monitor.alert_emails."""

    def check_resp(self, response: httpx.Response | None) -> tuple[MonitorState, int]:
        """Checks the response and returns the new state and consecutive fails. Also alerts if
        needed.
        """
        state = MonitorState.down
        if response:
            state = MonitorState.up
            # TODO: check assertions
        consecutive_fails = 0 if state == MonitorState.up else self.monitor.consecutive_fails + 1
        if consecutive_fails >= self.monitor.failures_before_alerting:
            self.alert()
        return state, consecutive_fails

    def put_log(self, state: MonitorState, status_code: int, latency: float):
        """
        Puts a log for the check. This method should only be called once per monitor check.
        """
        if self._put_log:
            raise Exception('Log already put! Do not call this method more than once in one run.')
        uptime_log = UptimeLog(
            monitor_id=f'{self.monitor.project_id}/{self.monitor.slug}',
            timestamp=self.now,
            status=state,
            resp_code=status_code,
            latency_secs=latency,
        )
        UptimeLogTable.put(uptime_log)
        self._put_log = True

    def run(self):
        """
        1. Make the request
        2. Check the response
        3. Update the monitor
        4. Save a log
        """
        if not self.monitor:
            log.info(f'Monitor {self.project_id}/{self.monitor_slug} not found, skipping')
            return

        log.info(f'Starting check for monitor: {self.monitor}')

        if self.monitor.state == MonitorState.paused:
            self.update_monitor()
            return

        # Make the request
        resp, latency = self.make_req()
        # Check the response (also kicks off alerts if needed)
        state, consecutive_fails = self.check_resp(resp)
        # Update the monitor
        self.update_monitor({'state': state, 'consecutive_fails': consecutive_fails})
        # Save a log
        self.put_log(state, resp.status_code if resp else 0, latency)
