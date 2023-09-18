import time
import alarm
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

from Sensor import Sensor
from BMESensor import BMESensor
from RainDropSensor import RainDropSensor
from PrecipitationSensor import PrecipitationSensor
from BatterySensor import BatterySensor

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
        return mqtt_client
    except Exception as ex:
        print(ex)
        mqtt_client = None
        return None

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

async def singleRun():
    sensors = []
    mqtt_client = None
    # Initialize sensor first, so we can detect changes while long running things like wifi happen
    if 'precipitation' in config:
        sensors.append(PrecipitationSensor(mqtt_client, config['precipitation']))
    if 'bme' in config:
        sensors.append(BMESensor(mqtt_client, config['bme']))
    if 'rain_drop' in config:
        sensors.append(RainDropSensor(mqtt_client, config['rain_drop']))
    if 'battery' in config:
        sensors.append(BatterySensor(mqtt_client, config['battery']))
    validSensors = []
    for sensor in sensors:
        try:
            # TODO: Convert to asyncio.gather([i.init() for i in sensors])
            await sensor.init()
            validSensors.append(sensor)
        except Exception as ex:
            print(ex)
            print("Error with sensor " + str(sensor) + " so we're skipping")
    sensors = validSensors
    validSensors = []
    # Initialize wifi and mqtt
    connectWifi()
    pixel.fill((0,0,0))
    print("Connected to %s!" % secrets["ssid"])
    mqtt_client = initMqtt()
    i = 0
    while mqtt_client is None and i < 5:
        print("Retry mqtt")
        time.sleep(1)
        mqtt_client = initMqtt()
        i += 1
    if i >= 5:
        print("Error initializing mqtt!!!")
        return
    # Done initializing networking

    for sensor in sensors:
        try:
            sensor.mqtt_client = mqtt_client
            sensor.advertiseSensor()
            validSensors.append(sensor)
        except Exception as ex:
            print(ex)
            print("Error with sensor " + str(sensor) + " so we're skipping")
    sensors = validSensors
    # Battery needs a delay between init and reading, else the state of charge is 0
    # Homeassistant needs a delay between advertising the sensor and sending the value
    time.sleep(0.2)
    for sensor in sensors:
        try:
            sensor.sendValue()
        except Exception as ex:
            print(ex)
            print("Error with sensor " + str(sensor) + " so we're skipping")
    mqtt_client.loop()
    # HomeAssistant isn't getting the sensor values, especially the ones that are published later without the sleep
    #time.sleep(0.5)
    mqtt_client.deinit()
    alarms = []
    #sensorAlarmLists = await asyncio.gather([i.alarms() for i in sensors])
    for sensor in sensors:
        alarms += await sensor.alarms()
    #for sensor in sensors:
    #    alarms += sensor.alarms()
    alarms.append(alarm.time.TimeAlarm(monotonic_time=time.monotonic()+Sensor.UPDATE_DELAY))
    alarm.exit_and_deep_sleep_until_alarms(*alarms)

asyncio.run(singleRun())
#showError()
#asyncio.run(runAsync())
