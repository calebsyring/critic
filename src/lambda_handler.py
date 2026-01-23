import logging

import mu

from critic.app import app
from critic.tasks import run_due_checks


log = logging.getLogger()


class ActionHandler(mu.ActionHandler):
    wsgi_app = app

    @staticmethod
    def run_due_checks(event, context):
        """Triggered by EventBridge rule, invokes `run_due_checks` task."""
        log.info('Invoking run_due_checks')
        run_due_checks.invoke()


# The entry point for AWS lambda has to be a function
entry = ActionHandler.on_event
