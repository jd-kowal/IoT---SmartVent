from flask import Flask, render_template, request, redirect, session, url_for, jsonify, Response
from datetime import timedelta, datetime
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

import netifaces as ni

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
        self.manual_until = None
        self.window_state_toggle = None
        self.automation_timer = {
            "start": None,
            "end": None
        }
        self.automation_timer_toggle = False

        self.is_window_open = None
        self.window_open_angle = 45
        self.window_closed_angle = 0

        self.user_pin = None
        self.admin_pin = None
        self.bearer_token = "?5Y?Js2QZ/K8h8@{pukvxd-q:gJqu+itO|ytvSsf]tu1=CPS.DKCH9*xps1b8OBv"

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
app_data.save()


def is_automiation_time() -> bool:
    """Return True if time is withing the automation time window"""
    start_time = datetime.strptime(app_data.automation_timer["start"], "%H:%M").time()
    end_time = datetime.strptime(app_data.automation_timer["end"], "%H:%M").time()
    current_time = datetime.now().time()

    if start_time <= end_time:
        # Range is confined to a single day
        return start_time <= current_time <= end_time
    else:
        # Range crosses midnight
        return current_time >= start_time or current_time <= end_time


def should_window_open() -> bool:
    if app_data.automation_timer_toggle and not is_automiation_time():
        print(f"> Time not met - automation={app_data.automation_timer}")
        return False

    if app_data.noise_level_toggle:
        for level, _ in sorted(app_data.noise_level_map.items(), key=lambda item: item[1]):
            if level == app_data.noise_level:
                break
            if level == app_data.noise_level_threshold:
                print(f"> Noise not met - thresh={app_data.noise_level_threshold} noise={app_data.noise_level}")
                return False
    if app_data.temperature_toggle and (app_data.temperature > float(app_data.temperature_threshold["max"]) or app_data.temperature < float(app_data.temperature_threshold["min"])):
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

    def enabled_symbol(toggle):
        enabled_symbols = ['✗', '✓']
        return enabled_symbols[int(bool(toggle))]

    print("\n<< Gathered data >>")
    set_noise_level()
    now = datetime.now()
    print(f"[{enabled_symbol(app_data.automation_timer_toggle)}] Time: {now.time().strftime('%H:%M')}")
    print(f"[{enabled_symbol(app_data.noise_level_toggle)}] Noise level: {app_data.noise_level}")
    set_air_quality()
    print(f"[{enabled_symbol(app_data.air_quality_toggle)}] Air quality: {app_data.air_quality_real} ({app_data.air_quality_user_friendly})")
    set_temperature()
    print(f"[{enabled_symbol(app_data.temperature_toggle)}] Temperature: {app_data.temperature}")

    if app_data.window_state_toggle == 'open':
        print("Window is force open by user")
        return
    if app_data.window_state_toggle == 'close':
        print("Window is force closed by user")
        return

    if app_data.manual_until is not None:
        if now.timestamp() <= app_data.manual_until:
            minutes_left = round((app_data.manual_until-now.timestamp())/60, 1)
            print(f"Window still will be manual for {minutes_left} minutes")
            return
        else:
            app_data.manual_until = None
            app_data.save()

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


DATA_INTERVAL_SECONDS = 60

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


def get_ip_address(interface):
    try:
        return ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
    except Exception:
        return "127.0.0.1"


def require_bearer_token(func):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            if session.get('logged_in') not in ['admin', 'user']:
                return redirect(url_for('index'))
            ip_address = get_ip_address("eth0")
            return redirect(f"http://{ip_address}:3000")

        token = auth_header.split("Bearer ")[1]
        if token != app_data.bearer_token:
            if session.get('logged_in') not in ['admin', 'user']:
                return redirect(url_for('index'))
            ip_address = get_ip_address("eth0")
            return redirect(f"http://{ip_address}:3000")

        return func(*args, **kwargs)
    return wrapper


def user_endpoint(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') not in ['admin', 'user']:
            return 'You have to be logged in', 401
        return f(*args, **kwargs)
    return decorated_function


def admin_endpoint(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('logged_in') not in ['admin', 'user']:
            return 'You have to be logged in', 401

        if session.get('logged_in') != 'admin':
            return 'You have to be an admin', 403

        return f(*args, **kwargs)
    return decorated_function


@app.route('/', methods=['GET'])
def index():
    show_set_pin = app_data.admin_pin is None
    create_user = not show_set_pin and app_data.user_pin is None
    # define_maps = app_data.air_quality_map['good'] is None
    show_login = True

    if 'logged_in' in session:
        if session['logged_in'] == 'user':
            return redirect(url_for('user_dashboard'))
        if session['logged_in'] == 'admin':
            return redirect(url_for('admin_dashboard'))

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
    if app_data.user_pin is not None:
        return '', 404

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
    return 'Success', 200


@app.route('/setAdminPin', methods=['POST'])
def set_admin_pin():
    if app_data.admin_pin is not None:
        return '', 404

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
@user_required
def settings():
    if session.get('logged_in') == 'user':
        return render_template(
            'settings_user.html',
            data={"role": "user"}
        )
    elif session.get('logged_in') == 'admin':
        return render_template(
            'settings_admin.html',
            data={"role": "admin"}
        )


@app.route('/settingsAdmin', methods=['GET'])
@admin_required
def settingsAdmin():

    return render_template(
        'settings_admin.html'
    )


@app.route('/mainMenu', methods=['GET'])
@user_required
def menu():

    if session['logged_in'] == 'user':
        return render_template(
            'main_menu.html',
            data={"role": "user"}
        )
    elif session['logged_in'] == 'admin':
        return render_template(
            'main_menu.html',
            data={"role": "admin"}
        )


@app.route('/userDashboard', methods=['GET'])
@user_required
def user_dashboard():
    return render_template('main_menu.html', data={"role": "user"})


@app.route('/adminDashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    return render_template('main_menu.html', data={"role": "admin"})


@app.route('/logout', methods=['GET'])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


@app.route('/getAirQuality', methods=['GET'])
@user_endpoint
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
@admin_endpoint
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


@app.route('/getAirQualityMap', methods=['GET'])
@admin_endpoint
def get_air_quality_map():
    return jsonify({'air_quality_map': app_data.air_quality_map}), 200


@app.route('/setAirQualityThreshold', methods=['POST'])
@user_endpoint
def set_air_quality_threshold():
    air_quality_threshold = request.json.get('air_quality_threshold')

    if air_quality_threshold is None:
        return 'Missing air_quality_threshold parameter', 400

    app_data.air_quality_threshold = air_quality_threshold
    app_data.save()
    return 'Success', 200


@app.route('/getAirQualityThreshold', methods=['GET'])
@user_endpoint
def get_air_quality_threshold():
    return jsonify({'air_quality_threshold': app_data.air_quality_threshold}), 200


@app.route('/setAirQualityToggle', methods=['POST'])
@user_endpoint
def set_air_quality_toggle():
    air_quality_toggle = request.json.get('air_quality_toggle')

    if air_quality_toggle is None:
        return 'Missing air_quality_toggle parameter', 400

    app_data.air_quality_toggle = air_quality_toggle
    app_data.save()
    return 'Success', 200


@app.route('/getAirQualityToggle', methods=['GET'])
@user_endpoint
def get_air_quality_toggle():
    return jsonify({'air_quality_toggle': app_data.air_quality_toggle}), 200


@app.route('/getNoiseLevel', methods=['GET'])
@user_endpoint
def get_noise_level():
    return jsonify({'noise_level': app_data.noise_level}), 200


def set_noise_level():
    noise_levels = []
    for _ in range(20):
        noise_levels.append(getNoiseLevel())
        sleep(0.1)
    print(f"Noise values: {[int(x) for x in noise_levels]}")
    for level, value in sorted(app_data.noise_level_map.items(), key=lambda item: item[1], reverse=True):
        if sum(noise_levels)/len(noise_levels) >= value:
            app_data.noise_level = level
            app_data.save()
            return


@app.route('/setNoiseLevelMap', methods=['POST'])
@admin_endpoint
def set_noise_level_map():
    try:
        data = request.get_json()

        if not data or 'low' not in data or 'medium' not in data or 'high' not in data:
            return jsonify({"error": "Invalid input. Must include low, medium, and high levels."}), 400

        for _, v in data.items():
            if v > 1 or v < 0:
                return jsonify({"error": "Invalid input. low, medium, and high levels must be between 0 and 1."}), 400

        app_data.noise_level_map = {
            "low": float(data.get("low")),
            "medium": float(data.get("medium")),
            "high": float(data.get("high"))
        }
        app_data.save()
        return jsonify({"message": "Noise level map updated successfully.", "noise_level_map": app_data.noise_level_map}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/getNoiseLevelMap', methods=['GET'])
@admin_endpoint
def get_noise_level_map():
    return jsonify({'noise_level_map': app_data.noise_level_map}), 200


@app.route('/setNoiseLevelThreshold', methods=['POST'])
@user_endpoint
def set_noise_level_threshold():
    noise_level_threshold = request.json.get('noise_level_threshold')

    if noise_level_threshold is None:
        return 'Missing noise_level_threshold parameter', 400

    app_data.noise_level_threshold = noise_level_threshold
    app_data.save()
    return 'Success', 200


@app.route('/getNoiseLevelThreshold', methods=['GET'])
@user_endpoint
def get_noise_level_threshold():
    return jsonify({'noise_level_threshold': app_data.noise_level_threshold}), 200


@app.route('/setNoiseLevelToggle', methods=['POST'])
@user_endpoint
def set_noise_level_toggle():
    noise_level_toggle = request.json.get('noise_level_toggle')

    if noise_level_toggle is None:
        return 'Missing noise_level_toggle parameter', 400

    app_data.noise_level_toggle = noise_level_toggle
    app_data.save()
    return 'Success', 200


@app.route('/getNoiseLevelToggle', methods=['GET'])
@user_endpoint
def get_noise_level_toggle():
    return jsonify({'noise_level_toggle': app_data.noise_level_toggle}), 200


@app.route('/getTemperature', methods=['GET'])
@user_endpoint
def get_temperature_level():
    return jsonify({'temperature': app_data.temperature}), 200


def set_temperature():
    temperature = getTemperature()
    app_data.temperature = round(temperature, 1)
    app_data.save()


@app.route('/setTemperatureThreshold', methods=['POST'])
@user_endpoint
def set_temperature_threshold():
    temperature_threshold = request.json.get('temperature_threshold')

    if temperature_threshold is None:
        return 'Missing temperature_threshold parameter', 400

    app_data.temperature_threshold = temperature_threshold
    app_data.save()
    return 'Success', 200


@app.route('/getTemperatureThreshold', methods=['GET'])
@user_endpoint
def get_temperature_threshold():
    return jsonify({'temperature_threshold': app_data.temperature_threshold}), 200


@app.route('/setTemperatureToggle', methods=['POST'])
@user_endpoint
def set_temperature_toggle():
    temperature_toggle = request.json.get('temperature_toggle')

    if temperature_toggle is None:
        return 'Missing temperature_toggle parameter', 400

    app_data.temperature_toggle = temperature_toggle
    app_data.save()
    return 'Success', 200


@app.route('/getTemperatureToggle', methods=['GET'])
@user_endpoint
def get_temperature_toggle():
    return jsonify({'temperature_toggle': app_data.temperature_toggle}), 200


@app.route('/setWindowStateTimer', methods=['POST'])
@user_endpoint
def set_window_state_timer():
    # window_state_timer is in minutes
    window_state_timer = request.json.get('window_state_timer')

    if window_state_timer is None:
        return 'Missing window_state_timer parameter', 400

    if 'state' not in window_state_timer or window_state_timer['state'] not in ['open', 'close']:
        return 'Incorrect "state" for window_state_timer parameter'

    timestamp = datetime.now().timestamp() + window_state_timer['time']*60
    state = window_state_timer['state']

    app_data.manual_until = timestamp
    app_data.window_state_toggle = 'auto'

    if state == 'open':
        if not app_data.is_window_open:
            set_window_angle(app_data.window_open_angle)
            app_data.is_window_open = True
        app_data.save()
        print("** Window Opened Manually (timed) **")
        return f'Successfully opened window for {window_state_timer} minutes', 200
    if state == 'close':
        if app_data.is_window_open:
            set_window_angle(app_data.window_closed_angle)
            app_data.is_window_open = False
        app_data.save()
        print("** Window Closed Manually (timed) **")
        return f'Successfully closed window for {window_state_timer} minutes', 200


@app.route('/setWindowStateToggle', methods=['POST'])
@user_endpoint
def set_window_state_toggle():
    window_state_toggle = request.json.get('window_state_toggle')

    if window_state_toggle is None:
        return 'Missing window_state_toggle parameter', 400

    if window_state_toggle not in ['open', 'close', 'auto']:
        return 'Incorrect window_state_toggle parameter', 400

    app_data.window_state_toggle = window_state_toggle
    app_data.manual_until = None

    if window_state_toggle == "close":
        if app_data.is_window_open:
            set_window_angle(app_data.window_closed_angle)
            app_data.is_window_open = False
        app_data.save()
        print("** Window Closed Manually **")
        return 'Successfully closed window', 200

    if window_state_toggle == "open":
        if not app_data.is_window_open:
            set_window_angle(app_data.window_open_angle)
            app_data.is_window_open = True
        app_data.save()
        print("** Window Open Manually **")
        return 'Successfully opened window', 200

    if window_state_toggle == "auto":
        app_data.save()
        print("** Window Now Working Automatically **")
        return 'Successfully set window state to automatic', 200


@app.route('/setAutomationTimer', methods=['POST'])
@user_endpoint
def set_automation_timer():
    automation_timer = request.json.get('automation_timer')

    if automation_timer is None:
        return 'Missing automation_timer parameter', 400

    if len(automation_timer.keys()) != 2:
        return 'Incorrect keys in automation_timer parameter', 400

    # Validate and reformat "start" and "end"
    for key in ['start', 'end']:
        if key not in automation_timer:
            return f'Missing {key} in automation_timer', 400
        try:
            # Parse and reformat to "%H:%M"
            parsed_time = datetime.strptime(automation_timer[key], '%H:%M').time()
            automation_timer[key] = parsed_time.strftime('%H:%M')
        except ValueError:
            return f'Invalid format for {key}, expected "%H:%M"', 400

    app_data.automation_timer = automation_timer
    app_data.save()
    return 'Success', 200


@app.route('/getAutomationTimer', methods=['GET'])
@user_endpoint
def get_automation_timer():
    return jsonify({'automation_timer': app_data.automation_timer}), 200


@app.route('/setAutomationTimerToggle', methods=['POST'])
@user_endpoint
def set_automation_timer_toggle():
    automation_timer_toggle = request.json.get('automation_timer_toggle')

    if automation_timer_toggle is None:
        return 'Missing automation_timer_toggle parameter', 400

    app_data.automation_timer_toggle = automation_timer_toggle
    app_data.save()
    return 'Success', 200


@app.route('/getAutomationTimerToggle', methods=['GET'])
@user_endpoint
def get_automation_timer_toggle():
    return jsonify({'automation_timer_toggle': app_data.automation_timer_toggle}), 200


@app.route('/isWindowOpen', methods=['GET'])
@user_endpoint
def get_is_window_open():
    data = {'is_window_open': app_data.is_window_open}
    if app_data.manual_until is not None:
        data['manual_until'] = app_data.manual_until
    return jsonify(data), 200


@app.route('/metrics', methods=['GET'])
@require_bearer_token
def metrics():
    air_quality_metrics = "\n".join(
        [f'air_quality_map{{quality="{key}"}} {value}' for key, value in app_data.air_quality_map.items()]
    )

    metrics = [
        "# HELP temperature_toggle Indicates if temperature monitoring is enabled.",
        "# TYPE temperature_toggle gauge",
        f"temperature_toggle {1 if app_data.temperature_toggle else 0}",

        "# HELP noise_level_toggle Indicates if noise level monitoring is enabled.",
        "# TYPE noise_level_toggle gauge",
        f"noise_level_toggle {1 if app_data.noise_level_toggle else 0}",

        "# HELP air_quality_toggle Indicates if air quality monitoring is enabled.",
        "# TYPE air_quality_toggle gauge",
        f"air_quality_toggle {1 if app_data.air_quality_toggle else 0}",

        "# HELP window_open_angle The angle of the window when it is open.",
        "# TYPE window_open_angle gauge",
        f"window_open_angle {app_data.window_open_angle}",

        "# HELP window_closed_angle The angle of the window when it is closed.",
        "# TYPE window_closed_angle gauge",
        f"window_closed_angle {app_data.window_closed_angle}",

        "# HELP automation_timer_toggle Indicates if the automation timer is enabled.",
        "# TYPE automation_timer_toggle gauge",
        f"automation_timer_toggle {1 if app_data.automation_timer_toggle else 0}",

        "# HELP is_window_open Indicates if the window is opend.",
        "# TYPE is_window_open gauge",
        f"is_window_open {1 if app_data.is_window_open else 0}",
        air_quality_metrics
    ]

    if app_data.temperature_threshold:
        metrics.append("# HELP temperature_threshold_min Minimum temperature threshold.")
        metrics.append("# TYPE temperature_threshold_min gauge")
        metrics.append(f"temperature_threshold_min {app_data.temperature_threshold['min']}")

        metrics.append("# HELP temperature_threshold_max Maximum temperature threshold.")
        metrics.append("# TYPE temperature_threshold_max gauge")
        metrics.append(f"temperature_threshold_max {app_data.temperature_threshold['max']}")

    metrics.append("# HELP temperature Current temperature.")
    metrics.append("# TYPE temperature gauge")
    metrics.append(f"temperature {app_data.temperature if app_data.temperature is not None else 'NaN'}")

    NOISE_LEVEL_MAP = {"low": 1, "medium": 2, "high": 3}
    noise_level_value = NOISE_LEVEL_MAP.get(app_data.noise_level_threshold, 0)
    metrics.append("# HELP noise_level Current noise level.")
    metrics.append("# TYPE noise_level gauge")
    metrics.append(f"noise_level {noise_level_value}")

    metrics.append("# HELP air_quality_real Real-time air quality value.")
    metrics.append("# TYPE air_quality_real gauge")
    metrics.append(f"air_quality_real {app_data.air_quality_real if app_data.air_quality_real is not None else 'NaN'}")

    return Response("\n".join(metrics), mimetype="text/plain")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
