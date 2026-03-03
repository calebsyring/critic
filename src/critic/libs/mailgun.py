import os

import httpx


class MailgunError(Exception):
    pass


def send_email(to_email: str, subject: str, text: str) -> None:
    # Send an email via Mailgun HTTP API.
    api_key = os.environ.get('MAILGUN_API_KEY')
    domain = os.environ.get('MAILGUN_DOMAIN')
    mail_from = os.environ.get('MAILGUN_FROM')

    if not api_key:
        raise MailgunError('Missing MAILGUN_API_KEY')
    if not domain:
        raise MailgunError('Missing MAILGUN_DOMAIN')
    if not mail_from:
        raise MailgunError('Missing MAILGUN_FROM')
    if not to_email:
        raise MailgunError('Missing recipient email')

    resp = httpx.post(
        f'https://api.mailgun.net/v3/{domain}/messages',
        auth=('api', api_key),
        data={
            'from': mail_from,
            'to': to_email,
            'subject': subject,
            'text': text,
        },
        timeout=10,
    )
    resp.raise_for_status()
