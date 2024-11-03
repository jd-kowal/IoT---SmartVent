import board
import adafruit_bme280
import RPi.GPIO as GPIO
import adafruit_busio
import struct
import time

def getTemperature():
    """Reads a single measurement from the Adafruit BME280 sensor, and returns the temperature in C."""
    i2c = board.I2C()
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

    temperature = bme280.temperature
    return temperature


def getNoiseLevel():
    """Reads a single measurement from the MOD-06638 sensor, and returns True if the noise is higher than limit."""
    SOUND_PIN = 11

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SOUND_PIN, GPIO.IN)

    if GPIO.input(SOUND_PIN):
        return True
    return False


def getAirQuality():
    """Initializes UART, reads a single PM2.5 measurement from the PMS5003 sensor, and returns the concentration in µg/m³."""
    uart = adafruit_busio.UART(board.TX, board.RX, baudrate=9600, timeout=2)

    # Check if at least 32 bytes are available in the UART buffer
    if uart.in_waiting >= 32:
        data = uart.read(32)
        if data and data[0] == 0x42 and data[1] == 0x4D:
            frame = struct.unpack(">HHHHHHHHHHHHHH", data[2:])
            pm2_5 = frame[3]  # PM2.5 concentration in µg/m³
            return pm2_5
    return None


def set_window_angle(degree):
    """Set a servo MOT-00484 on the right angel."""
    if degree>90 or degree<0:
        return False

    GPIO.setmode(GPIO.BOARD) # Sets the pin numbering system to use the physical layout
    SERVO_PIN = 33
    GPIO.setup(SERVO_PIN,GPIO.OUT)  # Sets up pin 33 to an output (instead of an input)
    p = GPIO.PWM(SERVO_PIN, 50)     # Sets up pin 33 as a PWM pin
    p.start(0)               # Starts running PWM on the pin and sets it to 0

    duty = 2 + (degree / 18)  # Przelicznik 2-12 dla 0-180 stopni
    p.ChangeDutyCycle(duty)
    time.sleep(0.5)  # Dajemy czas serwu na przemieszczenie się

    return None