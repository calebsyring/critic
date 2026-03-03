import logging

from critic.libs.mailgun import send_email
from critic.libs.slack import post_message, post_webhook
from critic.models import MonitorState, UptimeMonitorModel


log = logging.getLogger(__name__)


def _monitor_url(monitor: UptimeMonitorModel) -> str:
    return str(monitor.url)


def _monitor_label(monitor: UptimeMonitorModel) -> str:
    return f'{monitor.project_id}/{monitor.slug}'


def _send_slack(monitor: UptimeMonitorModel, text: str) -> None:
    for dest in monitor.alert_slack_channels:
        try:
            # If it looks like a webhook, use webhook mode otherwise treat as channel id/name.
            if dest.startswith(('http://', 'https://')):
                post_webhook(dest, text)
            else:
                post_message(dest, text)
        except Exception as e:
            log.exception(f'Failed to send Slack alert to {dest}: {e}')


def _send_email(monitor: UptimeMonitorModel, subject: str, text: str) -> None:
    for email in monitor.alert_emails:
        try:
            send_email(email, subject, text)
        except Exception as e:
            log.exception(f'Failed to send email alert to {email}: {e}')


def maybe_send_alerts(
    *,
    monitor: UptimeMonitorModel,
    prev_state: MonitorState,
    prev_consecutive_fails: int,
) -> None:
    # Decide whether to send alerts based on state transitions and fail thresholds.
    if monitor.state == MonitorState.paused:
        return

    label = _monitor_label(monitor)
    url = _monitor_url(monitor)

    # Recovery
    if prev_state == MonitorState.down and monitor.state == MonitorState.up:
        subject = f'CRITIC RECOVERY: {label}'
        text = f'Recovered: {label}\nURL: {url}'
        log.info(f'Sending recovery alert for {label}')
        _send_slack(monitor, text)
        _send_email(monitor, subject, text)
        return

    # Down alert
    if (
        monitor.state == MonitorState.down
        and monitor.consecutive_fails >= monitor.failures_before_alerting
    ):
        crossed_threshold = prev_consecutive_fails < monitor.failures_before_alerting
        became_down = prev_state != MonitorState.down
        if crossed_threshold or became_down:
            subject = f'CRITIC DOWN: {label}'
            text = (
                f'Down: {label}\n'
                f'URL: {url}\n'
                f'Consecutive fails: {monitor.consecutive_fails} '
                f'(threshold: {monitor.failures_before_alerting})'
            )
            log.info(f'Sending down alert for {label}')
            _send_slack(monitor, text)
            _send_email(monitor, subject, text)
