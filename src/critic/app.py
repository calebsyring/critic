import logging
import os
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, url_for

from critic.forms import CreateProjectForm
from critic.tables import ProjectTable


log = logging.getLogger()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-change-me')

# Demo-only storage (clears on server restart)
DEMO_MODE = os.environ.get('CRITIC_DEMO_MODE', '1') == '1'
_demo_projects: list[dict[str, str]] = []


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
    return render_template('dashboard.html', projects=_demo_projects if DEMO_MODE else [])


@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """"""
    return render_template('project.html', project_id=project_id)


@app.route('/monitor/<int:monitor_id>')
def monitor_detail(monitor_id):
    """"""
    return render_template('monitor.html', monitor_id=monitor_id)


@app.route('/create', methods=['GET', 'POST'])
def create():
    form = CreateProjectForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        if DEMO_MODE:
            _demo_projects.append({'id': str(uuid4()), 'name': name})
        else:
            ProjectTable.put({'id': str(uuid4()), 'name': name})
        flash('Project created successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create.html', form=form)


@app.route('/project/<project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project (demo mode)."""
    if DEMO_MODE:
        global _demo_projects
        _demo_projects = [p for p in _demo_projects if p['id'] != project_id]
        flash('Project deleted.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('delete_project.html', project_id=project_id)


@app.route('/monitor/<int:monitor_id>/pause', methods=['POST'])
def pause_monitor(monitor_id):
    """HTMX endpoint, no template needed later"""
    return render_template('pause_monitor.html', monitor_id=monitor_id)


@app.route('/logout')
def logout():
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
