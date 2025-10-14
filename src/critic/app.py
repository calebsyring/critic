from enum import Enum
import logging

from flask import Flask, jsonify, request
import mu
from pydantic import BaseModel, Field, HttpUrl, ValidationError, conint


log = logging.getLogger()

app = Flask(__name__)


@app.route('/')
def hello_world():
    return '<p>Hello, <strong>World</strong>!</p>'


@app.route('/log')
def logs_example():
    log.error('This is an error')
    log.warning('This is a warning')
    log.info('This is an info log')
    log.debug('This is a debug log')

    return 'Logs emitted at debug, info, warning, and error levels'


@app.route('/error')
def error():
    raise RuntimeError('Deliberate runtime error')


class ActionHandler(mu.ActionHandler):
    wsgi_app = app


# The entry point for AWS lambda has to be a function
lambda_handler = ActionHandler.on_event


class State(str, Enum):
    new = 'new'
    up = 'up'
    down = 'down'
    paused = 'paused'


class Assertions(BaseModel):
    status_code: conint(ge=100, le=599) | None = None
    body_contains: str | None = None


class MonitorIn(BaseModel):
    group_id: str | None = None
    alert_slack_channels: list[str] = Field(default_factory=list)
    alert_emails: list[str] = Field(default_factory=list)
    realert_interval: int = Field(..., description='seconds', ge=0)
    state: State = State.new
    failures_before_alerting: int = Field(1, ge=0)
    url: HttpUrl
    interval: int = Field(..., description='seconds', ge=1)
    timeout: int = Field(..., description='seconds', ge=1)
    assertions: Assertions | None = None


class PutBody(BaseModel):
    monitors: list[MonitorIn] = Field(default_factory=list)


@app.route('/group/<group_id>', methods=['PUT'])
def put_group(group_id: str):
    try:
        data = request.get_json(force=True, silent=False)
        body = PutBody(**data)

    except (TypeError, ValidationError) as e:
        detail = e.errors() if isinstance(e, ValidationError) else str(e)
        return jsonify({'error': 'invalid payload', 'detail': detail}), 400

    for m in body.monitors:
        if m.group_id is not None and m.group_id != group_id:
            return jsonify(
                {
                    'error': 'group_id mismatch',
                    'detail': f"monitor.group_id '{m.group_id}' != path '{group_id}'",
                }
            ), 400

    return jsonify(
        {
            'group_id': group_id,
            'received': [m.model_dump(mode='json') for m in body.monitors],
            'message': 'OK (skeleton) — parsed and validated; no DB yet',
        }
    ), 200


# Optional: quick sanity endpoint
@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({'status': 'ok'}), 200
