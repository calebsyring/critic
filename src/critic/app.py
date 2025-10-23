# Saving this for later.
# from critic.libs.store import put_monitor
import logging

from flask import Flask, jsonify, request
import mu
from pydantic import BaseModel, Field, ValidationError

from critic.libs.scheduler import run_due_once
from critic.libs.uptime import check_monitor

from .Monitor.MonitorIn import MonitorIn


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
        if m.project_id is not None and m.project_id != group_id:
            return jsonify(
                {
                    'error': 'group_id mismatch',
                    'detail': f"monitor.project_id '{m.project_id}' != path '{group_id}'",
                }
            ), 400

    return jsonify(
        {
            'group_id': group_id,
            'received': [m.model_dump(mode='json') for m in body.monitors],
            'message': 'OK (skeleton) — parsed and validated; no DB yet',
        }
    ), 200


# Create monitor endpoint
@app.route('/scheduler/run', methods=['POST'])
def scheduler_run():
    updated = run_due_once()
    return jsonify({'updated_count': len(updated), 'updated': updated}), 200


# Create monitor check endpoint
@app.route('/monitor/check', methods=['POST'])
def monitor_check():
    try:
        data = request.get_json(force=True, silent=False)
        m = MonitorIn(**data)
    except (TypeError, ValidationError) as e:
        detail = e.errors() if isinstance(e, ValidationError) else str(e)
        return jsonify({'error': 'invalid payload', 'detail': detail}), 400

    result = check_monitor(m).model_dump(mode='json')
    return jsonify({'result': result}), 200
