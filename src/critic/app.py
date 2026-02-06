import logging

from flask import Flask, render_template


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


@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/create')
def create_monitor():
    return render_template('create.html')


@app.route('/delete')
def delete_monitor():
    return render_template('delete.html')


if __name__ == '__main__':
    app.run(debug=True)
