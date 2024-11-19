from random import random


def getTemperature():
    val = round(random()*40, 1)
    return val


def getNoiseLevel():
    val = bool(round(random()))
    return val


def getAirQuality():
    val = int(random()*75)
    return val


def set_window_angle(degree):
    return True
