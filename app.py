from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta
import os
import json
from functools import wraps


initial_run = False


class Storage:
    def __init__(self):
        self.temperature_threshold = None
        self.air_quality_threshold = None
        self.noise_level_threshold = None
        self.air_quality = None
        self.noise_level = None
        self.window_state_timer = None
        self.window_state_toggle = None
        self.automation_timer = None

        self.user_pin = None
        self.admin_pin = None

    def load(self):
        if os.path.exists(APP_DATA_FILE) and os.path.getsize(APP_DATA_FILE) > 0:
            with open(APP_DATA_FILE, 'r') as f:
                data = json.load(f)
                for key, value in data.items():
                    setattr(self, key, value)

            if self.admin_pin is None:
                initial_run = True

    def save(self):
        with open(APP_DATA_FILE, 'w') as f:
            json.dump(self.__dict__, f, indent=4)

    def is_valid_pin(pin, length):
        pin = str(pin)
        return len(pin) == length and pin.isdigit()



app = Flask(__name__)
app.secret_key = os.urandom(24)

app.permanent_session_lifetime = timedelta(minutes=100)

APP_DATA_FILE = 'app_data.json'

app_data = Storage()
app_data.load()


def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') not in ['admin', 'user']:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') != 'admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/', methods=['GET'])
def index():
    show_set_pin = app_data.admin_pin is None
    show_login = True

    if 'logged_in' in session:
        show_login = False

    return render_template(
        'index.html',
        show_set_pin=show_set_pin,
        show_login=show_login,
    )


@app.route('/setUserPin', methods=['POST'])
@admin_required
def set_user_pin():
    if request.method == 'POST':
        pin1 = request.form.get('pin1')
        pin2 = request.form.get('pin2')

        if not pin1 or not pin2:
            return 'Both PINs are required.', 400

        if not Storage.is_valid_pin(pin1, 4) or not Storage.is_valid_pin(pin2, 4):
            return 'User PIN must be exactly 4 digits.', 400

        if pin1 != pin2:
            return 'User PINs do not match. Please try again.', 400

        app_data.user_pin = pin1
        app_data.save()
        return '', 204


@app.route('/setAdminPin', methods=['POST'])
def set_admin_pin():
    if request.method == 'POST':

        pin1 = request.form.get('pin1')
        pin2 = request.form.get('pin2')

        if not pin1 or not pin2:
            return 'Both PINs are required.', 400

        if not Storage.is_valid_pin(pin1, 8) or not Storage.is_valid_pin(pin2, 8):
            return 'Admin PIN must be exactly 8 digits.', 400

        if pin1 != pin2:
            return 'Admin PINs do not match. Please try again.', 400

        app_data.admin_pin = pin1
        app_data.save()

        initial_run = False

        return redirect(url_for('index'))


@app.route('/login', methods=['POST'])
def login():
    pin = request.form['pin']

    if pin == app_data.user_pin:
        session['logged_in'] = 'user'
        session.permanent = True
        return redirect(url_for('user_dashboard'))

    if pin == app_data.admin_pin:
        session['logged_in'] = 'admin'
        session.permanent = True
        return redirect(url_for('admin_dashboard'))

    return 'Invalid PIN', 403


@app.route('/userDashboard', methods=['GET'])
@user_required
def user_dashboard():
    return render_template('user_dashboard.html', data={"secret": "This is the user dashboard."})


@app.route('/adminDashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html', data={"secret": "This is the admin dashboard."})


@app.route('/logout', methods=['GET'])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


@app.route('/getAirQuality', methods=['GET'])
def get_air_quality():
    return jsonify({'air_quality': app_data.air_quality}), 200


@app.route('/getNoiseLevel', methods=['GET'])
def get_noise_level():
    return jsonify({'noise_level': app_data.noise_level}), 200


@app.route('/setTemperatureThreshold', methods=['POST'])
def set_temperature_threshold():
    temperature_threshold = request.json.get('temperature_threshold')

    if temperature_threshold is None:
        return 'Missing temperature_threshold parameter', 400

    app_data.temperature_threshold = temperature_threshold
    app_data.save()
    return '', 204


@app.route('/setAirQualityThreshold', methods=['POST'])
def set_air_quality_threshold():
    air_quality_threshold = request.json.get('air_quality_threshold')

    if air_quality_threshold is None:
        return 'Missing air_quality_threshold parameter', 400

    app_data.air_quality_threshold = air_quality_threshold
    app_data.save()
    return '', 204


@app.route('/setNoiseLevelThreshold', methods=['POST'])
def set_noise_level_threshold():
    noise_level_threshold = request.json.get('noise_level_threshold')

    if noise_level_threshold is None:
        return 'Missing noise_level_threshold parameter', 400

    app_data.noise_level_threshold = noise_level_threshold
    app_data.save()
    return '', 204


@app.route('/setWindowStateTimer', methods=['POST'])
def set_window_state_timer():
    window_state_timer = request.json.get('window_state_timer')

    if window_state_timer is None:
        return 'Missing window_state_timer parameter', 400

    app_data.window_state_timer = window_state_timer
    app_data.save()
    return '', 204


@app.route('/setWindowStateToggle', methods=['POST'])
def set_window_state_toggle():
    window_state_toggle = request.json.get('window_state_toggle')

    if window_state_toggle is None:
        return 'Missing window_state_toggle parameter', 400

    app_data.window_state_toggle = window_state_toggle
    app_data.save()
    return '', 204


@app.route('/setAutomationTimer', methods=['POST'])
def set_automation_timer():
    automation_timer = request.json.get('automation_timer')

    if automation_timer is None:
        return 'Missing automation_timer parameter', 400

    app_data.automation_timer = automation_timer
    app_data.save()
    return '', 204


@app.route('/metrics', methods=['GET'])
def metrics():
    return jsonify(app_data.__dict__), 200


if __name__ == '__main__':
    app.run(port=5000)
