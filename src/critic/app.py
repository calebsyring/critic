import logging
import os

from flask import Flask, jsonify, request
from monitor_utility import create_monitors, delete_monitors  # Import helpers
import mu


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


@app.route('/monitors/create')
def create_monitors_route():
    # SImple start to get monitor going
    table_name = os.environ.get('MONITOR_TABLE_NAME', 'Critic-Monitors')
    project_id = request.args.get('project_id', 'demo-project')
    prefix = request.args.get('prefix', 'demo')
    count = int(request.args.get('count', '10'))

    created = create_monitors(
        table_name=table_name,
        project_id=project_id,
        prefix=prefix,
        count=count,
        ddb=None,  # Uses a boto3 ddb resource
    )
    return jsonify({'created': created})


@app.route('/monitors/delete')
def delete_monitors_route():
    table_name = os.environ.get('MONITOR_TABLE_NAME', 'Critic-Monitors')
    project_id = request.args.get('project_id', 'demo-project')
    prefix = request.args.get('prefix', 'demo')

    deleted = delete_monitors(
        table_name=table_name,
        project_id=project_id,
        prefix=prefix,
        ddb=None,
    )
    return jsonify({'deleted': deleted})


class ActionHandler(mu.ActionHandler):
    wsgi_app = app


# The entry point for AWS lambda has to be a function
lambda_handler = ActionHandler.on_event
