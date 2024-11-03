#temeprature
# pip install adafruit - circuitpython - bme280

import board
import adafruit_bme280

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

temperature = bme280.temperature
humidity = bme280.humidity
print(f"Temperature: {temperature} C")
print(f"Humidity: {humidity} %")


#noise
import RPi.GPIO as GPIO

SOUND_PIN = 17  # wybierz odpowiedni pin GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(SOUND_PIN, GPIO.IN)

if GPIO.input(SOUND_PIN):
    print("Dźwięk wykryty!")
else:
    print("Cisza")

#pollution
# pip install pms5003

from pms5003 import PMS5003

pms5003 = PMS5003()
data = pms5003.read()
print(f"PM2.5: {data.pm_ug_per_m3(2.5)} µg/m³")