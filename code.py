# SPDX-FileCopyrightText: 2021 Melissa LeBlanc-Williams for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
SHTC3 Temperature/Humidity Sensor Example for
using CircuitPython with Home Assistant
Author: Melissa LeBlanc-Williams for Adafruit Industries
"""
print("hello")
import time
import ssl
import json
import alarm
import board
import digitalio
import socketpool
import wifi
import neopixel
import countio
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_bme280 import basic as adafruit_bme280
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.fill((20, 0, 0))
SWITCH_DELAY = 0.05
PUBLISH_DELAY = 10
EXPIRE_DELAY = 5*60
MQTT_TOPIC = "state/temp-sensor"

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
# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    showError()
    raise

def initBme():
    try:
        print("Initializing BME")
        i2c = board.STEMMA_I2C()
        bme = adafruit_bme280.Adafruit_BME280_I2C(i2c)
        bme.mode = adafruit_bme280.MODE_SLEEP
        return True, bme
    except Exception as ex:
        print(ex)
        i2c = None
        bme = None
        return False, bme

# TODO: Add board.A2 input which is the analog input for a rain drop sensor

# Initialize the rain drop detection sensor
def initRainDrop():
    try:
        dropDIn = digitalio.DigitalInOut(board.A1)
        dropDIn.direction = digitalio.Direction.INPUT
        dropDIn.pull = digitalio.Pull.UP
        return True, dropDIn
    except:
        return False, None
    
def isRaining(dropDIn):
    return not dropDIn.value

def rainDropOutput(dropDIn):
    if isRaining(dropDIn):
        output = {"state": "ON"}
    else:
        output = {"state": "OFF"}
    return json.dumps(output)

def initPrecipitation():
    try:
        precipitationIn = digitalio.DigitalInOut(board.A0)
        precipitationIn.direction = digitalio.Direction.INPUT
        precipitationIn.pull = digitalio.Pull.UP
        return True, precipitationIn
    except:
        return False, None

def getTopic(sensorType, postfix="/state"):
    return "homeassistant/sensor/" + secrets["topic_prefix"] + sensorType + postfix
def getBinaryTopic(sensorType, postfix="/state"):
    return "homeassistant/binary_sensor/" + secrets["topic_prefix"] + sensorType + postfix

def publishRainDropSensor(mqtt_client):
    topic = getBinaryTopic("rain_drop", "/config")
    payload = {
        "name": secrets['name_prefix'] + "Rain Drop",
        "device_class": "moisture",
        "state_topic": getBinaryTopic("rain_drop"),
        "payload_available": "online",
        "payload_not_available": "offline",
        "expire_after": EXPIRE_DELAY,
        "unique_id": secrets['topic_prefix'] + "raindropsensor",
        "value_template": "{{ value_json.state }}"}
    mqtt_client.publish(topic, json.dumps(payload))
def publishPrecipitationSensor(mqtt_client):
    topic = getTopic("precipitation", "/config")
    payload = {
        "name": secrets['name_prefix'] + "Precipitation",
        "device_class": "precipitation",
        "state_topic": getTopic("precipitation"),
        "unit_of_measurement": "mm",
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": secrets['topic_prefix'] + "raingauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.precipitation | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))

def publishSensors(mqtt_client):
    topic = getTopic("temperature", "/config")
    prefix = secrets['topic_prefix']
    name_prefix = secrets['name_prefix']
    payload = {
        "name": name_prefix + "Temperature",
        "device_class": "temperature",
        "state_topic": getTopic("temperature"),
        "unit_of_measurement": "°C",
        "expire_after": EXPIRE_DELAY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": prefix + "temperaturegauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.temperature | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))
    topic = getTopic("humidity", "/config")
    payload = {
        "name": name_prefix + "Humidity",
        "device_class": "humidity",
        "state_topic": getTopic("humidity"),
        "unit_of_measurement": "%rH",
        "expire_after": EXPIRE_DELAY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": prefix + "humiditygauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.humidity | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))
    topic = getTopic("pressure", "/config")
    payload = {
        "name": name_prefix + "Pressure",
        "device_class": "pressure",
        "state_topic": getTopic("pressure"),
        "unit_of_measurement": "hPa",
        "expire_after": EXPIRE_DELAY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": prefix + "pressuregauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.pressure | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))

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

def run():
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
    initialized, precipitationIn = initPrecipitation()
    while not initialized:
        print("Retry Precipitation")
        time.sleep(1)
        initialized, precipitationIn = initPrecipitation()
    initialized, dropDIn = initRainDrop()
    while not initialized:
        print("Retry Rain Drop")
        time.sleep(1)
        initialized, dropDIn = initRainDrop()
    state_topic = "homeassistant/sensor/temperature/state"
    publishSensors(mqtt_client)
    lastbmeupdate = 0
    lastPrecipitationIn = precipitationIn.value
    rainCount = 0
    rainPublished = False
    dropPublished = False
    lastDropValue = dropDIn.value
    _, bme = initBme()
    while True:
        if time.monotonic() > lastbmeupdate + PUBLISH_DELAY:
            if not dropPublished and dropDIn.value != lastDropValue:
                    publishRainDropSensor(mqtt_client)
                    dropPublished = True
            if dropPublished:
                print(rainDropOutput(dropDIn))
                mqtt_client.publish(getBinaryTopic("rain_drop"), rainDropOutput(dropDIn))
            if bme is None:
                _, bme = initBme()
            else:
                lastbmeupdate = time.monotonic()
                temperature = bme.temperature
                relative_humidity = bme.relative_humidity
                pressure = bme.pressure
                output = {
                    "temperature": temperature}
                mqtt_client.publish(getTopic("temperature"), json.dumps(output))
                output = {
                    "humidity": relative_humidity}
                mqtt_client.publish(getTopic("humidity"), json.dumps(output))
                output = {
                    "pressure": pressure}
                mqtt_client.publish(getTopic("pressure"), json.dumps(output))
                print("Published")
        precipitationVal = precipitationIn.value
        if precipitationVal != lastPrecipitationIn:
            if not rainPublished:
                publishPrecipitationSensor(mqtt_client)
            lastPrecipitationIn = precipitationVal
            rainCount += 1
            print(rainCount)
            output = {
                "precipitation": rainCount / 3.467}
            mqtt_client.publish(getTopic("precipitation"), json.dumps(output))
                
        time.sleep(SWITCH_DELAY)
while True:
    run()