

import time
import ssl
import json
import asyncio
import alarm
import board
import digitalio
import socketpool
import wifi
import neopixel
import countio
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_bme280 import basic as adafruit_bme280

from BMESensorLoop import BMESensorLoop
from RainDropSensorLoop import RainDropSensorLoop
from PrecipitationSensorLoop import PrecipitationSensorLoop
from OccupancySensorLoop import OccupancySensorLoop
from BatteryLevelLoop import BatteryLevelLoop

from config import config

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.fill((20, 0, 0))

def showFinish():
    while True:
        pixel.fill((0, 255, 0))
        time.sleep(0.5)
        pixel.fill((0, 0, 0))
        time.sleep(0.5)
def showError():
    while True:
        pixel.fill((255, 0, 0))
        time.sleep(0.5)
        pixel.fill((0, 0, 0))
        time.sleep(0.5)
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    showError()
    raise

def initMqtt():
    try:
        print("Initializing Mqtt")
        # Create a socket pool
        pool = socketpool.SocketPool(wifi.radio)
        # Set up a MiniMQTT Client
        mqtt_client = MQTT.MQTT(
            broker=secrets["mqtt_broker"],
            port=secrets["mqtt_port"],
            username=secrets["mqtt_username"],
            password=secrets["mqtt_password"],
            socket_pool=pool,
            ssl_context=ssl.create_default_context(),
        )
        print("Attempting to connect to %s" % mqtt_client.broker)
        mqtt_client.connect()
        return True, mqtt_client
    except Exception as ex:
        print(ex)
        mqtt_client = None
        return False, None

async def runAsync():
    needRetry = True
    while needRetry:
        try:
            wifi.radio.connect(secrets["ssid"], secrets["password"])
            needRetry = False
        except Exception as ex:
            print(ex)
            time.sleep(1)
    pixel.fill((0,0,0))
    print("Connected to %s!" % secrets["ssid"])
    initialized, mqtt_client = initMqtt()
    while not initialized:
        print("Retry mqtt")
        time.sleep(1)
        initialized, mqtt_client = initMqtt()
    toRun = []
    if 'bme' in config:
        toRun.append(BMESensorLoop(mqtt_client, config['bme']))
    if 'rain_drop' in config:
        toRun.append(RainDropSensorLoop(mqtt_client, config['rain_drop']))
    if 'precipitation' in config:
        toRun.append(PrecipitationSensorLoop(mqtt_client, config['precipitation']))
    if 'occupancy' in config:
        toRun.append(OccupancySensorLoop(mqtt_client, config['occupancy']))
    if 'battery' in config:
        toRun.append(BatteryLevelLoop(mqtt_client, config['battery']))
    toRun = [i.run() for i in toRun]
    await asyncio.gather(
        *toRun,
        return_exceptions=True)

asyncio.run(runAsync())
