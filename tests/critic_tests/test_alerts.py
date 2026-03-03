from unittest import mock

from critic.alerts import maybe_send_alerts
from critic.libs.testing import UptimeMonitorFactory
from critic.libs.uptime import UptimeCheck
from critic.models import MonitorState


class TestAlerts:
    # These tests are validating the alert decision logic.
    # Actual slack and email delivery is mocked until we decide how we want to set that up.

    @mock.patch('critic.alerts._send_email')
    @mock.patch('critic.alerts._send_slack')
    def test_no_alert_below_threshold(self, m_slack, m_email):
        # Below Threshold -> Do Not Alert
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.down,
            consecutive_fails=1,
            failures_before_alerting=2,
            alert_slack_channels=['C123'],
            alert_emails=['a@example.com'],
        )

        maybe_send_alerts(
            monitor=monitor,
            prev_state=MonitorState.up,
            prev_consecutive_fails=0,
        )

        m_slack.assert_not_called()
        m_email.assert_not_called()

    @mock.patch('critic.alerts._send_email')
    @mock.patch('critic.alerts._send_slack')
    def test_alert_on_threshold_cross(self, m_slack, m_email):
        # Cross Threshold -> Alert Once
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.down,
            consecutive_fails=2,
            failures_before_alerting=2,
            alert_slack_channels=['C123'],
            alert_emails=['a@example.com'],
        )

        maybe_send_alerts(
            monitor=monitor,
            prev_state=MonitorState.up,
            prev_consecutive_fails=1,
        )

        m_slack.assert_called_once()
        m_email.assert_called_once()

    @mock.patch('critic.alerts._send_email')
    @mock.patch('critic.alerts._send_slack')
    def test_recovery_alert(self, m_slack, m_email):
        # Down state to up state -> Send Recovery Alert
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.up,
            consecutive_fails=0,
            failures_before_alerting=2,
            alert_slack_channels=['C123'],
            alert_emails=['a@example.com'],
        )

        maybe_send_alerts(
            monitor=monitor,
            prev_state=MonitorState.down,
            prev_consecutive_fails=3,
        )

        m_slack.assert_called_once()
        m_email.assert_called_once()

    @mock.patch('critic.alerts._send_email')
    @mock.patch('critic.alerts._send_slack')
    def test_paused_no_alert(self, m_slack, m_email):
        # Paused Monitors -> No Alerts
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.paused,
            consecutive_fails=999,
            failures_before_alerting=1,
            alert_slack_channels=['C123'],
            alert_emails=['a@example.com'],
        )

        maybe_send_alerts(
            monitor=monitor,
            prev_state=MonitorState.down,
            prev_consecutive_fails=999,
        )

        m_slack.assert_not_called()
        m_email.assert_not_called()

    @mock.patch('critic.alerts._send_email')
    @mock.patch('critic.alerts._send_slack')
    def test_no_repeat_alert_when_already_over_threshold(self, m_slack, m_email):
        # Spam Prevention -> No Duplicate Alerts unless state change
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.down,
            consecutive_fails=5,
            failures_before_alerting=2,
            alert_slack_channels=['C123'],
            alert_emails=['a@example.com'],
        )

        maybe_send_alerts(
            monitor=monitor,
            prev_state=MonitorState.down,
            prev_consecutive_fails=4,
        )

        m_slack.assert_not_called()
        m_email.assert_not_called()


class TestUptimeAlertHook:
    # These tests validate where alerting happens in the UptimeCheck.run() flow.
    # The key invariant is race safety. Only the winning conditional update should alert + log.

    @mock.patch('critic.libs.uptime.UptimeLogTable.put')
    @mock.patch('critic.libs.uptime.UptimeMonitorTable.update')
    @mock.patch('critic.libs.uptime.UptimeCheck.make_req')
    @mock.patch('critic.libs.uptime.UptimeCheck.alert')
    def test_no_alert_if_update_fails(self, m_alert, m_make_req, m_update, m_put_log):
        # If update fails -> No alert + No Log
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.up,
            consecutive_fails=1,
            failures_before_alerting=2,
        )

        m_make_req.return_value = (None, 0.1)  # failing check -> down
        m_update.return_value = False  # simulate race condition

        UptimeCheck(monitor.project_id, monitor.slug).run()

        m_alert.assert_not_called()
        m_put_log.assert_not_called()

    @mock.patch('critic.libs.uptime.UptimeLogTable.put')
    @mock.patch('critic.libs.uptime.UptimeMonitorTable.update')
    @mock.patch('critic.libs.uptime.UptimeCheck.make_req')
    @mock.patch('critic.libs.uptime.UptimeCheck.alert')
    def test_alert_only_after_successful_update(self, m_alert, m_make_req, m_update, m_put_log):
        # If update succeeds -> Alert + Write Log
        monitor = UptimeMonitorFactory.put(
            state=MonitorState.up,
            consecutive_fails=1,
            failures_before_alerting=2,
        )

        m_make_req.return_value = (None, 0.1)
        m_update.return_value = True

        UptimeCheck(monitor.project_id, monitor.slug).run()

        m_alert.assert_called_once()
        m_put_log.assert_called_once()
