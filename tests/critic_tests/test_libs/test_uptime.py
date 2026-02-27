from datetime import UTC, datetime
import logging

from freezegun import freeze_time
import httpx
import pytest

from critic.libs.assertions import Assertion
from critic.libs.testing import UptimeMonitorFactory
from critic.libs.uptime import MonitorNotFoundError, UptimeCheck
from critic.models import MonitorState, UptimeLog, UptimeMonitorModel
from critic.tables import UptimeLogTable, UptimeMonitorTable


class TestUptimeCheck:
    def test_not_found(self):
        with pytest.raises(MonitorNotFoundError):
            UptimeCheck('6033aa47-a9f7-4d7f-b7ff-a11ba9b34474', 'my-monitor')

    def test_duplicate_update(self):
        monitor = UptimeMonitorFactory.put()
        check = UptimeCheck(str(monitor.project_id), monitor.slug)
        check.update_monitor()
        with pytest.raises(Exception, match='Monitor already updated'):
            check.update_monitor()

    def test_duplicate_log(self):
        monitor = UptimeMonitorFactory.put()
        check = UptimeCheck(str(monitor.project_id), monitor.slug)
        check.put_log(MonitorState.up, 200, 0.1, None)
        with pytest.raises(Exception, match='Log already put'):
            check.put_log(MonitorState.up, 200, 0.1, None)

    def test_race_condition(self, httpx_mock):
        monitor = UptimeMonitorFactory.put(next_due_at='2026-02-10 11:50:00Z')

        # Initialize the check
        check = UptimeCheck(str(monitor.project_id), monitor.slug)

        # Simulate a check running after the first one initialized
        UptimeMonitorTable.update(
            monitor.project_id, monitor.slug, updates={'next_due_at': '2026-02-10 12:00:00Z'}
        )

        # Run the check
        httpx_mock.add_response()
        check.run()

        # Next due at remains the same
        monitor = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        assert monitor.next_due_at == datetime(2026, 2, 10, 12, 0, 0, tzinfo=UTC)

        # No log is created
        logs = UptimeLogTable.query(f'{monitor.project_id}/{monitor.slug}')
        assert len(logs) == 0

    def test_run_up(self, caplog, httpx_mock):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=1, failures_before_alerting=2, state=MonitorState.up
        )

        caplog.set_level(logging.INFO)

        time_to_check = monitor.next_due_at

        httpx_mock.add_response()
        UptimeCheck(str(monitor.project_id), monitor.slug).run()

        # check ddb entries
        assert 'Starting check' in caplog.text  # make sure method is sending log
        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)

        # check that monitor is up, next due at is later, and consecutive fails is 0 because passing
        assert response.state == MonitorState.up
        assert response.next_due_at > time_to_check
        assert response.consecutive_fails == 0

        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)[-1]

        # check logging stuff
        assert response.status == MonitorState.up
        assert response.resp_code > 0
        assert response.latency_secs > 0
        assert response.error_message is None

    def test_down_with_consec_fails_above_threshold(self, httpx_mock):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=1,
            failures_before_alerting=2,
            state=MonitorState.down,
        )

        httpx_mock.add_exception(httpx.TimeoutException('Connection timed out'))
        UptimeCheck(str(monitor.project_id), monitor.slug).run()

        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        # Monitor should be down with 2 consec fails
        assert response.state == MonitorState.down
        assert response.consecutive_fails == 2

        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)[-1]
        # log should have resp of 0 since there was a timeout
        assert response.status == MonitorState.down
        assert response.resp_code == 0

    def test_down_with_consec_fails_below_threshold(self, httpx_mock):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=0,
            failures_before_alerting=2,
            state=MonitorState.up,
        )

        httpx_mock.add_exception(httpx.TimeoutException('Connection timed out'))

        UptimeCheck(str(monitor.project_id), monitor.slug).run()

        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        assert response.state == MonitorState.down
        assert response.consecutive_fails == 1

        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)[-1]
        # log should have resp of 0 since there was a timeout
        assert response.status == MonitorState.down
        assert response.resp_code == 0
        assert response.error_message == 'Connection Timeout'

    def test_paused(self):
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            consecutive_fails=0,
            failures_before_alerting=2,
            state=MonitorState.paused,
        )
        time_to_check = monitor.next_due_at

        UptimeCheck(str(monitor.project_id), monitor.slug).run()

        response: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        assert response.next_due_at > time_to_check
        monitor_id = f'{monitor.project_id}/{monitor.slug}'
        response: UptimeLog = UptimeLogTable.query(monitor_id)
        # does not have item because no log is created since the monitor is paused
        assert response == []

    @freeze_time('2026-02-01 12:00:13', tz_offset=0)
    def test_old_next_due_at(self, httpx_mock):
        httpx_mock.add_response()

        # Pretend critic went down for a month (from Jan 1st to Feb 1st). Next due at is much older
        # than we would expect.
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            next_due_at='2026-01-01 12:00:00Z',
            frequency_mins=5,
        )

        UptimeCheck(str(monitor.project_id), monitor.slug).run()

        # Next due at should be calculated from the current time
        monitor: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)
        assert monitor.next_due_at == datetime(2026, 2, 1, 12, 5, 0, tzinfo=UTC)

    def test_assertion_fails(self, httpx_mock):
        httpx_mock.add_response()

        # Pretend critic went down for a month (from Jan 1st to Feb 1st). Next due at is much older
        # than we would expect.
        monitor: UptimeMonitorModel = UptimeMonitorFactory.put(
            next_due_at='2026-01-01 12:00:00Z',
            frequency_mins=5,
            state=MonitorState.up,
            assertions=[Assertion(assertion_string="body contains 'foo'")],
        )

        UptimeCheck(str(monitor.project_id), monitor.slug).run()
        monitor: UptimeMonitorModel = UptimeMonitorTable.get(monitor.project_id, monitor.slug)

        assert monitor.state == MonitorState.down
