import logging
import os
from uuid import UUID, uuid4

from flask import Flask, flash, redirect, render_template, request, url_for

from critic.forms import CreateProjectForm
from critic.models import UptimeMonitorModel
from critic.tables import ProjectTable, UptimeMonitorTable


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
    return render_template('dashboard.html')


@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """"""
    return render_template('project.html', project_id=project_id)


@app.route('/monitor/<int:monitor_id>')
def monitor_detail(monitor_id):
    """"""
    return render_template('monitor.html', monitor_id=monitor_id)


@app.route('/create-project', methods=['GET', 'POST'])
def create_project():
    form = CreateProjectForm()
    if form.validate_on_submit():
        ProjectTable.put({'id': str(uuid4()), 'name': form.name.data.strip()})
        flash('Project created successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_project.html', form=form)


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


@app.route('/project/<project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project."""
    return render_template('delete.html')


@app.route('/monitor/<int:monitor_id>/pause', methods=['POST'])
def pause_monitor(monitor_id):
    """HTMX endpoint, no template needed later"""
    return render_template('pause_monitor.html', monitor_id=monitor_id)


@app.route('/logout')
def logout():
    """This is temporary"""
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
