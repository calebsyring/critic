import os

import httpx


class SlackError(Exception):
    pass


def post_webhook(webhook_url: str, text: str) -> None:
    # Send a Slack message via Incoming Webhook URL.
    if not webhook_url:
        raise SlackError('Missing webhook_url')

    resp = httpx.post(
        webhook_url,
        json={'text': text},
        timeout=10,
    )
    resp.raise_for_status()


def post_message(channel: str, text: str) -> None:
    # Send a Slack message using chat.postMessage (requires SLACK_BOT_TOKEN).
    token = os.environ.get('SLACK_BOT_TOKEN')
    if not token:
        raise SlackError('Missing SLACK_BOT_TOKEN')

    resp = httpx.post(
        'https://slack.com/api/chat.postMessage',
        headers={'Authorization': f'Bearer {token}'},
        json={'channel': channel, 'text': text},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get('ok'):
        raise SlackError(f'Slack API error: {data.get("error")}')
