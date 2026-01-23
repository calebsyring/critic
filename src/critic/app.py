import logging

from flask import Flask
import mu

from critic.tasks import run_due_checks


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

    @staticmethod
    def run_due_checks(event, context):
        """Triggered by EventBridge rule, invokes `run_due_checks` task."""
        log.info('Invoking run_due_checks')
        run_due_checks.invoke()


# The entry point for AWS lambda has to be a function
lambda_handler = ActionHandler.on_event
