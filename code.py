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
PUBLISH_DELAY = 20
EXPIRE_DELAY = 5*60
MQTT_TOPIC = "state/temp-sensor"
USE_DEEP_SLEEP = False

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

def initRain():
    try:
        rainIn = digitalio.DigitalInOut(board.A0)
        rainIn.direction = digitalio.Direction.INPUT
        rainIn.pull = digitalio.Pull.UP
        return True, rainIn
    except:
        rainIn = None
        return False, rainIn

def publish_sensor(mqtt_client):
    discovery_prefix = "homeassistant"
    component = "sensor"
    object_id = "temperature"
    topic = discovery_prefix + "/" + component + "/" + object_id + "/config"
    payload = {
        "name": "Temperature",
        "device_class": "temperature",
        "state_topic": "homeassistant/sensor/temperature/state",
        "unit_of_measurement": "°C",
        "expire_after": EXPIRE_DELAY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": "outsidetemperaturegauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.temperature | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))
    topic = discovery_prefix + "/" + component + "/humidity/config"
    payload = {
        "name": "Humidity",
        "device_class": "humidity",
        "state_topic": "homeassistant/sensor/humidity/state",
        "unit_of_measurement": "%rH",
        "expire_after": EXPIRE_DELAY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": "humiditygauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.humidity | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))
    topic = discovery_prefix + "/" + component + "/pressure/config"
    payload = {
        "name": "Pressure",
        "device_class": "pressure",
        "state_topic": "homeassistant/sensor/pressure/state",
        "unit_of_measurement": "hPa",
        "expire_after": EXPIRE_DELAY,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": "pressuregauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.pressure | round(1) }}"}
    mqtt_client.publish(topic, json.dumps(payload))
    topic = discovery_prefix + "/" + component + "/precipitation/config"
    payload = {
        "name": "Precipitation",
        "device_class": "precipitation",
        "state_topic": "homeassistant/sensor/precipitation/state",
        "unit_of_measurement": "mm",
        "payload_available": "online",
        "payload_not_available": "offline",
        "unique_id": "raingauge",
        "suggested_display_precision": "1",
        "value_template": "{{ value_json.precipitation | round(1) }}"}
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
    initialized, rainIn = initRain()
    while not initialized:
        print("Retry Rain")
        time.sleep(1)
        initialized, rainIn = initRain()
    state_topic = "homeassistant/sensor/temperature/state"
    publish_sensor(mqtt_client)
    lastbmeupdate = 0
    lastRainIn = rainIn.value
    rainCount = 0
    _, bme = initBme()
    while True:
        if time.monotonic() > lastbmeupdate + PUBLISH_DELAY:
            if bme is None:
                _, bme = initBme()
            else:
                lastbmeupdate = time.monotonic()
                temperature = bme.temperature
                relative_humidity = bme.relative_humidity
                pressure = bme.pressure
                output = {
                    "temperature": temperature}
                mqtt_client.publish("homeassistant/sensor/temperature/state", json.dumps(output))
                output = {
                    "humidity": relative_humidity}
                mqtt_client.publish("homeassistant/sensor/humidity/state", json.dumps(output))
                output = {
                    "pressure": pressure}
                mqtt_client.publish("homeassistant/sensor/pressure/state", json.dumps(output))
                print("Published")
        rainVal = rainIn.value
        if rainVal != lastRainIn:
            lastRainIn = rainVal
            rainCount += 1
            print(rainCount)
            output = {
                "precipitation": rainCount / 3.467}
            mqtt_client.publish("homeassistant/sensor/precipitation/state", json.dumps(output))
            
        time.sleep(SWITCH_DELAY)

        #if USE_DEEP_SLEEP:
        #    mqtt_client.disconnect()
        #    pause = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + PUBLISH_DELAY)
        #    alarm.exit_and_deep_sleep_until_alarms(pause)
        #else:
        #    last_update = time.monotonic()
        #    while time.monotonic() < last_update + PUBLISH_DELAY:
        #        mqtt_client.loop()
while True:
    run()