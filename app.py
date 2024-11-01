from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from datetime import timedelta
import os
import json

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.permanent_session_lifetime = timedelta(minutes=100)

PIN_FILE = 'pins.json'
stored_pins = {'user': None, 'admin': None}

def is_valid_pin(pin, length):
    return len(pin) == length and pin.isdigit()

def load_pins():
    global stored_pins
    if os.path.exists(PIN_FILE):
        if os.path.getsize(PIN_FILE) > 0:
            with open(PIN_FILE, 'r') as f:
                data = json.load(f)
                stored_pins['user'] = data.get('user_pin')
                stored_pins['admin'] = data.get('admin_pin')

def save_pins(user_pin=None, admin_pin=None):
    if stored_pins['user'] is not None and user_pin is None:
        user_pin = stored_pins['user']
    if stored_pins['admin'] is not None and admin_pin is None:
        admin_pin = stored_pins['admin']

    with open(PIN_FILE, 'w') as f:
        json.dump({'user_pin': user_pin, 'admin_pin': admin_pin}, f)

@app.route('/', methods=['GET'])
def index():
    load_pins()

    show_set_user_pin = stored_pins['user'] is None
    show_set_admin_pin = stored_pins['admin'] is None

    show_user_login = True
    show_admin_login = True

    if 'logged_in' in session:
        if session['logged_in'] == 'user':
            show_set_user_pin = False
            show_user_login = False
        elif session['logged_in'] == 'admin':
            show_set_admin_pin = False
            show_admin_login = False

    return render_template(
        'index.html',
        show_set_user_pin=show_set_user_pin,
        show_set_admin_pin=show_set_admin_pin,
        show_user_login=show_user_login,
        show_admin_login=show_admin_login
    )

@app.route('/setUserPin', methods=['GET', 'POST'])
def set_user_pin():
    if request.method == 'POST':
        pin1 = request.form['pin1']
        pin2 = request.form['pin2']

        if not is_valid_pin(pin1, 4) or not is_valid_pin(pin2, 4):
            return 'User PIN must be exactly 4 digits.', 400

        if pin1 != pin2:
            return 'User PINs do not match. Please try again.', 400

        save_pins(user_pin=pin1)
        load_pins()
        return redirect(url_for('index'))

    return render_template('set_user_pin.html')

@app.route('/setAdminPin', methods=['GET', 'POST'])
def set_admin_pin():
    if request.method == 'POST':
        pin1 = request.form['pin1']
        pin2 = request.form['pin2']

        if not is_valid_pin(pin1, 8) or not is_valid_pin(pin2, 8):
            return 'Admin PIN must be exactly 8 digits.', 400

        if pin1 != pin2:
            return 'Admin PINs do not match. Please try again.', 400

        save_pins(admin_pin=pin1)
        load_pins()
        return redirect(url_for('index'))

    return render_template('set_admin_pin.html')

@app.route('/login', methods=['POST'])
def login():
    pin = request.form['pin']

    if pin == stored_pins['user']:
        session['logged_in'] = 'user'
        session.permanent = True
        return redirect(url_for('user_dashboard'))

    if pin == stored_pins['admin']:
        session['logged_in'] = 'admin'
        session.permanent = True
        return redirect(url_for('admin_dashboard'))

    return 'Invalid PIN', 403


    return 'Invalid Admin PIN', 403

@app.route('/userDashboard', methods=['GET'])
def user_dashboard():
    if session.get('logged_in') != 'user':
        return redirect(url_for('index'))

    return render_template('user_dashboard.html', data={"secret": "This is the user dashboard."})

@app.route('/adminDashboard', methods=['GET'])
def admin_dashboard():
    if session.get('logged_in') != 'admin':
        return redirect(url_for('index'))

    return render_template('admin_dashboard.html', data={"secret": "This is the admin dashboard."})

@app.route('/logout', methods=['GET'])
def logout():
    if session.get('logged_in') in ['user', 'admin']:
        session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/setTemperatureThreshold', methods=['GET'])
def set_temperature_threshold():
    return '', 204

@app.route('/setAirQualityThreshold', methods=['GET'])
def set_air_quality_threshold():
    return '', 204

@app.route('/setNoiseLevelThreshold', methods=['GET'])
def set_noise_level_threshold():
    return '', 204

@app.route('/getAirQuality', methods=['GET'])
def get_air_quality():
    return '', 204

@app.route('/getNoiseLevel', methods=['GET'])
def get_noise_level():
    return '', 204

@app.route('/setWindowStateTimer', methods=['GET'])
def set_window_state_timer():
    return '', 204

@app.route('/setWindowStateToggle', methods=['GET'])
def set_window_state_toggle():
    return '', 204

@app.route('/setAutomationTimer', methods=['GET'])
def set_automation_timer():
    return '', 204

@app.route('/metrics', methods=['GET'])
def metrics():
    return '', 204

load_pins()

if __name__ == '__main__':
    app.run(port=5000)
