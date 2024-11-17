# IoT---SmartVent

# Currently you can see UI on http://localhost:5000/settingsUser and http://localhost:5000/mainMenu


Run with:
```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt

python3 webapp.py
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



