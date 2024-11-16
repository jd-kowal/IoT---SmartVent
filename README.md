# IoT---SmartVent

Run with:
```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt

FLASK_APP=app.py
FLASK_ENV=development
flask run
```


# 1.enable i2c and uart: <br>
- sudo raspi-config <br>
- enable i2c and uart in config file <br>
- reboot rapsberry pi<br>

# 2.install required libraries: <br>
- sudo pip3 install adafruit-circuitpython-bme280 adafruit-circuitpython-busdevice
- sudo apt update
- sudo apt install python3-rpi.gpio
- pip3 install pyserial

# 3. run the scrip:
- sudo python3 main.py



