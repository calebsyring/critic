import logging

from flask import Flask, redirect, render_template, url_for


log = logging.getLogger()

app = Flask(__name__)


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


@app.route('/create')
def create():
    """"""
    return render_template('create.html')


@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """"""
    return render_template('delete_project.html', project_id=project_id)


@app.route('/monitor/<int:monitor_id>/pause', methods=['POST'])
def pause_monitor(monitor_id):
    """HTMX endpoint, no template needed later"""
    return render_template('pause_monitor.html', monitor_id=monitor_id)


@app.route('/logout', methods=['POST'])
def logout():
    """This will redirect the user back to dashboard for now."""
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
