from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta
import os
import json
from functools import wraps

from temp import getTemperature, getNoiseLevel, getAirQuality, set_window_angle
# from sensors import getTemperature, getNoiseLevel, getAirQuality, set_window_angle

from time import sleep
# import time
# import atexit
# import threading

from apscheduler.schedulers.background import BackgroundScheduler

initial_run = False


class Storage:
    def __init__(self):
        self.temperature_threshold = {
            "min": 10,
            "max": 31
        }
        self.temperature_toggle = True
        self.temperature = None
        self.noise_level_threshold = "medium"
        self.noise_level_toggle = True
        self.noise_level = None
        self.noise_level_map = {
            "low": 0,
            "medium": 0.3,
            "high": 0.6
        }
        self.air_quality_threshold = "moderate"
        self.air_quality_toggle = True
        self.air_quality_real = None
        self.air_quality_user_friendly = None
        self.air_quality_map = {
            "good": 0,
            "moderate": 25,
            "poor": 50
        }
        self.window_state_timer = None
        self.window_state_toggle = None
        self.automation_timer = {
            "start": None,
            "end": None
        }
        self.automation_timer_toggle = None

        self.is_window_open = None
        self.window_open_angle = 45
        self.window_closed_angle = 0

        self.user_pin = None
        self.admin_pin = None

    def get_air_quality(self, pm_value):
        # Go from worst to best air quality in map
        for level, value in sorted(self.air_quality_map.items(), key=lambda item: item[1], reverse=True):
            if value is not None and pm_value >= value:
                return level
        return "None"

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


def should_window_open():
    if app_data.noise_level_toggle:
        for level, _ in sorted(app_data.noise_level_map.items(), key=lambda item: item[1]):
            if level == app_data.noise_level:
                break
            if level == app_data.noise_level_threshold:
                print(f"> Noise not met - thresh={app_data.noise_level_threshold} noise={app_data.noise_level}")
                return False
    # bool(app_data.noise_level) > bool(app_data.noise_level_threshold):
    #     print(f"> Noise not met - thresh={app_data.noise_level_threshold} noise={app_data.noise_level}")
        return False
    if app_data.temperature_toggle and (app_data.temperature > app_data.temperature_threshold["max"] or app_data.temperature < app_data.temperature_threshold["min"]):
        print(f"> Temp not met - thresh={app_data.temperature_threshold} temp={app_data.temperature}")
        return False
    if app_data.air_quality_toggle:
        for level, _ in sorted(app_data.air_quality_map.items(), key=lambda item: item[1]):
            if level == app_data.air_quality_user_friendly:
                break
            if level == app_data.air_quality_threshold:
                print(f"> Air not met - thresh={app_data.air_quality_threshold} air={app_data.air_quality_user_friendly}")
                return False
    return True


def setVals():
    if app_data.air_quality_map is None:
        return
    set_noise_level()
    print("Noise level:", app_data.noise_level)
    set_air_quality()
    print("Air quality:", app_data.air_quality_user_friendly)
    print("Air quality:", app_data.air_quality_real)
    set_temperature()
    print("Temperature:", app_data.temperature)

    if should_window_open():
        if not app_data.is_window_open:
            set_window_angle(app_data.window_open_angle)
            app_data.is_window_open = True
            app_data.save()
            print("** Window Opened **")
        return

    if app_data.is_window_open:
        set_window_angle(app_data.window_closed_angle)
        app_data.is_window_open = False
        app_data.save()
        print("** Window Closed **")
    return


DATA_INTERVAL_SECONDS = 6

scheduler = BackgroundScheduler()
scheduler.add_job(func=setVals, trigger="interval", seconds=DATA_INTERVAL_SECONDS)
scheduler.start()


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
    create_user = not show_set_pin and app_data.user_pin is None
    # define_maps = app_data.air_quality_map['good'] is None
    show_login = True

    if 'logged_in' in session:
        show_login = False

    return render_template(
        'index.html',
        show_set_pin=show_set_pin,
        show_login=show_login,
        create_user=create_user,
        air_quality_map=app_data.air_quality_map,
        # define_maps=define_maps
    )


@app.route('/setUserPin', methods=['POST'])
# @admin_required
def set_user_pin():
    if request.method == 'POST':
        data = request.get_json()

        pin1 = data.get('pin1')
        pin2 = data.get('pin2')

        if not pin1 or not pin2:
            return jsonify({"error": "Both PINs are required."}), 400

        if not Storage.is_valid_pin(pin1, 4) or not Storage.is_valid_pin(pin2, 4):
            return jsonify({"error": "User PIN must be exactly 4 digits."}), 400

        if pin1 != pin2:
            return jsonify({"error": "User PINs do not match. Please try again."}), 400

        app_data.user_pin = pin1
        app_data.save()
        return '', 204


@app.route('/setAdminPin', methods=['POST'])
def set_admin_pin():
    if request.method == 'POST':
        data = request.get_json()

        pin1 = data.get('pin1')
        pin2 = data.get('pin2')

        if not pin1 or not pin2:
            return 'Both PINs are required.', 400

        if not Storage.is_valid_pin(pin1, 8) or not Storage.is_valid_pin(pin2, 8):
            return 'Admin PIN must be exactly 8 digits.', 400

        if pin1 != pin2:
            return 'Admin PINs do not match. Please try again.', 400

        app_data.admin_pin = pin1
        app_data.save()

        initial_run = False

        return '', 200


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    pin = data['pin']

    if pin == app_data.user_pin:
        session['logged_in'] = 'user'
        session.permanent = True
        return redirect(url_for('user_dashboard'))

    if pin == app_data.admin_pin:
        session['logged_in'] = 'admin'
        session.permanent = True
        return redirect(url_for('admin_dashboard'))

    return 'Invalid PIN', 403


@app.route('/settingsUser', methods=['GET'])
def settings():

    return render_template(
        'settings_user.html'
    )


@app.route('/mainMenu', methods=['GET'])
def menu():

    return render_template(
        'main_menu.html'
    )


@app.route('/userDashboard', methods=['GET'])
@user_required
def user_dashboard():
    return render_template('main_menu.html')


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
    return jsonify({'air_quality': app_data.air_quality_user_friendly}), 200


def set_air_quality():
    tmp_air_quality = getAirQuality()
    app_data.air_quality_real = tmp_air_quality
    app_data.air_quality_user_friendly = app_data.get_air_quality(
            tmp_air_quality
        )
    app_data.save()


@app.route('/setAirQualityMap', methods=['GET', 'POST'])
def set_air_quality_map():

    if request.method == 'GET':
        return render_template('set_air_quality_map.html', air_quality_map=app_data.air_quality_map)
    elif request.method == 'POST':
        try:
            data = request.get_json()

            if not data or 'good' not in data or 'moderate' not in data or 'poor' not in data:
                return jsonify({"error": "Invalid input. Must include good, moderate, and poor levels."}), 400

            app_data.air_quality_map = {
                "good": data.get("good"),
                "moderate": data.get("moderate"),
                "poor": data.get("poor")
            }
            app_data.save()
            return jsonify({"message": "Air quality map updated successfully.", "air_quality_map": app_data.air_quality_map}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 400


@app.route('/setAirQualityThreshold', methods=['POST'])
def set_air_quality_threshold():
    air_quality_threshold = request.json.get('air_quality_threshold')

    if air_quality_threshold is None:
        return 'Missing air_quality_threshold parameter', 400

    app_data.air_quality_threshold = air_quality_threshold
    app_data.save()
    return '', 204


@app.route('/setAirQualityToggle', methods=['POST'])
def set_air_quality_toggle():
    air_quality_toggle = request.json.get('air_quality_toggle')

    if air_quality_toggle is None:
        return 'Missing air_quality_toggle parameter', 400

    app_data.air_quality_toggle = air_quality_toggle
    app_data.save()
    return '', 204


@app.route('/getNoiseLevel', methods=['GET'])
def get_noise_level():
    return jsonify({'noise_level': app_data.noise_level}), 200


def set_noise_level():
    noise_levels = []
    for _ in range(20):
        noise_levels.append(getNoiseLevel())
        sleep(0.1)
    print(noise_levels)
    for level, value in sorted(app_data.noise_level_map.items(), key=lambda item: item[1], reverse=True):
        if sum(noise_levels)/len(noise_levels) >= value:
            app_data.noise_level = level
            app_data.save()
            return


@app.route('/setNoiseLevelThreshold', methods=['POST'])
def set_noise_level_threshold():
    noise_level_threshold = request.json.get('noise_level_threshold')

    if noise_level_threshold is None:
        return 'Missing noise_level_threshold parameter', 400

    app_data.noise_level_threshold = noise_level_threshold
    app_data.save()
    return '', 204


@app.route('/setNoiseLevelToggle', methods=['POST'])
def set_noise_level_toggle():
    noise_level_toggle = request.json.get('noise_level_toggle')

    if noise_level_toggle is None:
        return 'Missing noise_level_toggle parameter', 400

    app_data.noise_level_toggle = noise_level_toggle
    app_data.save()
    return '', 204


@app.route('/getTemperature', methods=['GET'])
def get_temperature_level():
    return jsonify({'temperature': app_data.temperature}), 200


def set_temperature():
    temperature = getTemperature()
    app_data.temperature = round(temperature, 1)
    app_data.save()


@app.route('/setTemperatureThreshold', methods=['POST'])
def set_temperature_threshold():
    temperature_threshold = request.json.get('temperature_threshold')

    if temperature_threshold is None:
        return 'Missing temperature_threshold parameter', 400

    app_data.temperature_threshold = temperature_threshold
    app_data.save()
    return '', 204


@app.route('/setTemperatureToggle', methods=['POST'])
def set_temperature_toggle():
    temperature_toggle = request.json.get('temperature_toggle')

    if temperature_toggle is None:
        return 'Missing temperature_toggle parameter', 400

    app_data.temperature_toggle = temperature_toggle
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

    if window_state_toggle:
        print('Close window')

    return '', 204


@app.route('/setAutomationTimer', methods=['POST'])
def set_automation_timer():
    automation_timer = request.json.get('automation_timer')

    if automation_timer is None:
        return 'Missing automation_timer parameter', 400

    app_data.automation_timer = automation_timer
    app_data.save()
    return '', 204


@app.route('/setAutomationTimerToggle', methods=['POST'])
def set_automation_timer_toggle():
    automation_timer_toggle = request.json.get('automation_timer_toggle')

    if automation_timer_toggle is None:
        return 'Missing automation_timer_toggle parameter', 400

    app_data.automation_timer_toggle = automation_timer_toggle
    app_data.save()
    return '', 204


@app.route('/isWindowOpen', methods=['GET'])
def get_is_window_open():
    return jsonify({'is_window_open': app_data.is_window_open}), 200


@app.route('/metrics', methods=['GET'])
def metrics():
    return jsonify(app_data.__dict__), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
