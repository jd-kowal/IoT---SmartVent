
# 1.enable i2c and uart: <br>
- sudo raspi-config <br>
- enable i2c and uart in config file <br>
- reboot rapsberry pi<br>
 
# 2.install required libraries: <br>
- sudo pip3 install adafruit-circuitpython-bme280 adafruit-circuitpython-busdevice
- sudo apt update
- sudo apt install python3-rpi.gpio

# 3. run the scrip:
- sudo python3 main.py






