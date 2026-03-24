import logging
import os
from uuid import UUID

from flask import Flask, flash, redirect, render_template, request, url_for

from critic.models import UptimeMonitorModel
from critic.tables import UptimeMonitorTable


log = logging.getLogger()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-change-me')


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


@app.route('/login')
def login():
    """login with level 12 Auth"""
    return render_template('login.html')


@app.route('/')
def dashboard():
    """Overview of Monitors"""
    monitors = sorted(
        UptimeMonitorTable.scan(),
        key=lambda monitor: (str(monitor.project_id), monitor.slug),
    )
    table_name = UptimeMonitorTable.name()
    log.warning('Dashboard loading monitors from %s, count=%s', table_name, len(monitors))
    return render_template('dashboard.html', monitors=monitors, table_name=table_name)


@app.route('/create-monitor', methods=['GET', 'POST'])
def create_monitor():
    """Create a monitor."""
    if request.method == 'POST':
        project_id = request.form['project_id']
        slug = request.form['slug']
        url = request.form['url']
        frequency_mins = int(request.form['frequency_mins'])

        monitor = UptimeMonitorModel(
            project_id=UUID(project_id),
            slug=slug,
            url=url,
            frequency_mins=frequency_mins,
        )
        UptimeMonitorTable.put(monitor)

        flash('Monitor created successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_monitor.html')


@app.route('/logout')
def logout():
    """This is temporary"""
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
