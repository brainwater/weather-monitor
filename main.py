import time
import ssl
import json
import asyncio
import supervisor
import board
import digitalio
import socketpool
import wifi
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT

from Sensor import Sensor

from config import config

if 'alarm' in config:
    import alarm
if 'bme' in config:
    from BMESensor import BMESensor
if 'rain_drop' in config:
    from RainDropSensor import RainDropSensor
if 'precipitation' in config:
    from PrecipitationSensor import PrecipitationSensor
if 'battery' in config:
    from BatterySensor import BatterySensor
if 'pressure' in config:
    from PressureSensor import PressureSensor
if 'valve' in config:
    from ValveSensor import ValveSensor

if hasattr(board, 'NEOPIXEL'):
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
    pixel.fill((20, 0, 0))

def showFinish():
    if not hasattr(board, 'NEOPIXEL'):
        return
    while True:
        pixel.fill((0, 255, 0))
        time.sleep(0.5)
        pixel.fill((0, 0, 0))
        time.sleep(0.5)
def showError():
    if not hasattr(board, 'NEOPIXEL'):
        return
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

def initMqtt(mqtt=None):
    if mqtt is not None and mqtt.is_connected():
        return mqtt
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
        if hasattr(board, 'NEOPIXEL'):
            pixel.fill((50,0,0))
        print(ex)
    while not wifi.radio.connected:
        if not hasattr(board, 'NEOPIXEL'):
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
            if hasattr(board, 'NEOPIXEL'):
                pixel.fill((0,0,0))
        if not isConnected:
            if hasattr(board, 'NEOPIXEL'):
                pixel.fill((50,0,0))
            try:
                connectWifi()
                if wifi.radio.connected:
                    mqtt_client.reconnect()
                    if mqttConnected(mqtt_client):
                        if 'NEOPIXEL' in board:
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
    if 'pressure' in config:
        sensors.append(PressureSensor(mqtt_client, config['pressure']))
    if 'valve' in config:
        sensors.append(ValveSensor(mqtt_client, config['valve']))
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
    mqtt_client = None
    sensorerrors = []
    ADVERTISE_DELAY = 100
    # Make time since last advertise time be longer than ADVERTISE_DELAY
    lastadvertise = 0.0 - (2*ADVERTISE_DELAY)
    while True:
        connectWifi()
        if hasattr(board, 'NEOPIXEL'):
            pixel.fill((0,0,0))
        print("Connected to %s!" % secrets["ssid"])
        mqtt_client = initMqtt(mqtt_client)
        i = 0
        while mqtt_client is None and i < 5:
            print("Retry mqtt")
            time.sleep(1)
            mqtt_client = initMqtt(mqtt_client)
            i += 1
        if i >= 5:
            print("Error initializing mqtt!!!")
            return
        # Done initializing networking
        for sensor in sensors:
            sensor.mqtt_client = mqtt_client
        mqtt_client.loop()
        if time.monotonic() > lastadvertise + ADVERTISE_DELAY:
            for sensor in sensors:
                try:
                    sensor.advertiseSensor()
                    validSensors.append(sensor)
                except Exception as ex:
                    print(ex)
                    print("Error with sensor " + str(sensor) + " so we're skipping")
                    sensorerrors.append(sensor)
            sensors = validSensors
            validSensors = []
            lastadvertise = time.monotonic()
        # Battery needs a delay between init and reading, else the state of charge is 0
        # Homeassistant needs a delay between advertising the sensor and sending the value
        mqtt_client.loop(0.2)
        #time.sleep(0.2)
        for sensor in sensors:
            try:
                sensor.sendValue()
            except Exception as ex:
                print(ex)
                print("Error with sensor " + str(sensor) + " so we're skipping")
        mqtt_client.loop()
        #  HomeAssistant isn't getting the sensor values, especially the ones that are published later without the sleep
        #  time.sleep(0.5)
        #mqtt_client.deinit()
        if 'alarm' in config:
            alarms = []
            #sensorAlarmLists = await asyncio.gather([i.alarms() for i in sensors])
            for sensor in sensors:
                alarms += await sensor.alarms()
            alarms.append(alarm.time.TimeAlarm(monotonic_time=time.monotonic()+Sensor.UPDATE_DELAY))
            alarm.exit_and_deep_sleep_until_alarms(*alarms)
        elif len(sensorerrors) > 0:
            # Reset to hopefully resolve sensor error(s)
            supervisor.reload()

asyncio.run(singleRun())
#showError()
#asyncio.run(runAsync())