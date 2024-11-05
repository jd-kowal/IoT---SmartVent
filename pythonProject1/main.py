import board
from adafruit_bme280 import basic as adafruit_bme280
import RPi.GPIO as GPIO
import struct
import time
import serial


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
    noise_detected = GPIO.input(SOUND_PIN)
    return noise_detected == GPIO.HIGH

def getAirQuality():
    port = "/dev/serial0"  # Default UART port on Raspberry Pi
    baudrate = 9600  # Default baud rate for the PMS5003 sensor

    try:
        # Initialize UART with specified port and baud rate
        with serial.Serial(port, baudrate=baudrate, timeout=2) as uart:
            # Check if there are at least 32 bytes available in the UART buffer
            if uart.in_waiting >= 32:
                data = uart.read(32)

                # Verify the start of the frame (PMS5003 uses 0x42 and 0x4D as start bytes)
                if data and data[0] == 0x42 and data[1] == 0x4D:
                    # Unpack the data frame based on PMS5003 format
                    frame = struct.unpack(">HHHHHHHHHHHHHH", data[2:])
                    pm2_5 = frame[3]  # PM2.5 concentration in µg/m³
                    return pm2_5
    except serial.SerialException as e:
        print(f"UART error: {e}")

    return None
    # """Initializes UART, reads a single PM2.5 measurement from the PMS5003 sensor, and returns the concentration in µg/m³."""
    # uart = adafruit_busio.UART(board.TX, board.RX, baudrate=9600, timeout=2)
    # if uart.in_waiting >= 32:
    #     data = uart.read(32)
    #     if data and data[0] == 0x42 and data[1] == 0x4D:
    #         frame = struct.unpack(">HHHHHHHHHHHHHH", data[2:])
    #         pm2_5 = frame[3]  # PM2.5 concentration in µg/m³
    #         return pm2_5
    # return None

def set_window_angle(degree):
    """Set a servo MOT-00484 to a specified angle."""
    if degree > 90 or degree < 0:
        print("Invalid angle. Must be between 0 and 90.")
        return False

    GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering
    SERVO_PIN = 33
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz frequency
    pwm.start(0)  # Start PWM with 0 duty cycle

    try:
        duty_cycle = 2 + (degree / 18)  # Convert angle to duty cycle for 0-90 degree range
        pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(0.5)  # Wait for the servo to reach position
        pwm.ChangeDutyCycle(0)  # Stop sending PWM signal
    finally:
        pwm.stop()
    return True

def main():
    """Main function to read sensor values and control the servo."""
    try:
        # Read temperature
        #temperature = getTemperature()
        #print(f"Temperature: {temperature:.2f} °C")

        # Read noise level
        noise_detected = getNoiseLevel()
        print("Noise Detected:", "Yes" if noise_detected else "No")

        # Read air quality (PM2.5 concentration)
        air_quality = getAirQuality()
        if air_quality is not None:
            print(f"PM2.5 Concentration: {air_quality} µg/m³")
        else:
            print("Air Quality: Sensor data not available.")

        # Set servo angle (e.g., 45 degrees)
        angle = 45
        if set_window_angle(angle):
            print(f"Servo set to {angle} degrees.")

    finally:
        GPIO.cleanup()  # Ensure GPIO cleanup to avoid resource leaks

# Run the main function if this file is executed
if __name__ == "__main__":
    main()
