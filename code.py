

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
import ipaddress
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
    pool = None
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
            keep_alive=10
        )
        print("Attempting to connect to %s" % mqtt_client.broker)
        mqtt_client.connect()
        return pool, mqtt_client
    except Exception as ex:
        print(ex)
        mqtt_client = None
        return pool, None

def isConnected():
    return wifi.radio.connected

def connectWifi():
    print("Checking/connecting wifi")
    print("Attempting to connect")
    try:
        wifi.radio.connect(secrets['ssid'], secrets['password'])
    except Exception as ex:
        pixel.fill((50,0,0))
        print(ex)
    while not wifi.radio.connected:
        pixel.fill((50,0,0))
        try:
            wifi.radio.connect(secrets['ssid'], secrets['password'])
        except Exception as ex:
            print(ex)
            time.sleep(0.5)
    if wifi.radio.connected:
        print("Connection successful!")

def mqttConnected(mqtt_client):
    if not wifi.radio.connected:
        return False
    try:
        resp = mqtt_client.ping()
    except MQTT.MMQTTException as ex:
        print(ex)
        print("MQTTException when pinging server!")
        return False
    return mqtt_client.is_connected()

async def mqttCheckLoop(mqtt_client):
    while True:
        isConnected = False
        try:
            isConnected = mqttConnected(mqtt_client)
        except Exception as ex:
            print(ex)
            print("Exception when checking mqtt connection!")
        print("Connected? ", isConnected)
        if isConnected:
            pixel.fill((0,0,0))
        if not isConnected:
            pixel.fill((50,0,0))
            try:
                connectWifi()
                if wifi.radio.connected:
                    mqtt_client.reconnect()
                    if mqttConnected(mqtt_client):
                        pixel.fill((0,0,0))
                else:
                    print("Wifi disconnected!")
            except Exception as ex:
                print(ex)
                print("Exception when trying to reconnect!")
        await asyncio.sleep(10)

async def runAsync():
    connectWifi()
    pixel.fill((0,0,0))
    print("Connected to %s!" % secrets["ssid"])
    pool, mqtt_client = initMqtt()
    while mqtt_client is None:
        print("Retry mqtt")
        time.sleep(1)
        pool, mqtt_client = initMqtt()
    #sp = socketpool.SocketPool(wifi.radio)
    #print(pool.getaddrinfo("homeassistant.local", 1883, 0, pool.SOCK_STREAM))
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
    toRun.append(mqttCheckLoop(mqtt_client))
    await asyncio.gather(
        *toRun,
        return_exceptions=True)

asyncio.run(runAsync())
showError()
