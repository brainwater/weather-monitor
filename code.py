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
UPDATE_DELAY = 2
ADVERTISE_DELAY = 6*60
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

def occupancyOutput(occupancyIn):
    if occupancyIn.value:
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

def initOccupancy():
    try:
        inPin = digitalio.DigitalInOut(board.A3)
        inPin.direction = digitalio.Direction.INPUT
        inPin.pull = digitalio.Pull.DOWN
        # Don't need uart unless I'm getting more detailed info or changing settings
        #uart = busio.UART(board.TX, board.RX, baudrate=115200, bits=8)
        return True, inPin
    except:
        print("Error initializing occupancy sensor!")
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
def publishOccupancySensor(mqtt_client):
    topic = getBinaryTopic("occupancy", "/config")
    payload = {
        "name": secrets['name_prefix'] + "Occupancy",
        "device_class": "occupancy",
        "state_topic": getBinaryTopic("occupancy"),
        "payload_available": "online",
        "payload_not_available": "offline",
        "expire_after": EXPIRE_DELAY,
        "unique_id": secrets['topic_prefix'] + "raindropsensor",
        "value_template": "{{ value_json.state }}"}
    mqtt_client.publish(topic, json.dumps(payload))    
def publishBMESensors(mqtt_client):
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

def runBME(bme, lastbmeupdate, lastbmeadvertised, mqtt_client):
    if time.monotonic() > lastbmeadvertised + ADVERTISE_DELAY:
        lastbmeadvertised = time.monotonic()
        if bme is None:
            _, bme = initBme()
        if bme is not None:
            publishBMESensors(mqtt_client)
    if bme is not None and time.monotonic() > lastbmeupdate + UPDATE_DELAY:
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
        lastbmeupdate = time.monotonic()
    return bme, lastbmeupdate, lastbmeadvertised

def runDrop(dropDIn, lastdropupdate, lastdropadvertised, lastDropValue, dropPublished, mqtt_client):
    if not dropPublished:
        if dropDIn is None:
            # Initialize rain drop sensor
            _, dropDIn = initRainDrop()
            if dropDIn is not None:
                lastDropValue = dropDIn.value
        elif lastDropValue != dropDIn.value:
            # Rain Drop sensor detected a change, indicating the sensor is hooked up
            print("Decteded first change of rain drop sensor, starting advertising!")
            publishRainDropSensor(mqtt_client)
            dropPublished = True
    if dropPublished and time.monotonic() > lastdropadvertised + ADVERTISE_DELAY:
        # Advertise rain drop sensor with autodiscovery periodically
        print("Readvertising rain drop sensor")
        publishRainDropSensor(mqtt_client)
        lastdropadvertised = time.monotonic()
    if dropPublished and time.monotonic() > lastdropupdate + UPDATE_DELAY:
        # Do regular update of rain drop sensor value
        print(rainDropOutput(dropDIn))
        mqtt_client.publish(getBinaryTopic("rain_drop"), rainDropOutput(dropDIn))
        lastdropupdate = time.monotonic()
    return dropDIn, lastdropupdate, lastdropadvertised, lastDropValue, dropPublished

def runPrecipitation(precipitationIn, lastPrecipitationUpdate, lastPrecipitationAdvertised, precipitationPublished, rainCount, lastPrecipitationIn, mqtt_client):
    if precipitationIn is None:
        _, precipitationIn = initPrecipitation()
        lastPrecipitationIn = precipitationIn.value
    if precipitationIn is not None:
        if precipitationPublished and time.monotonic() > lastPrecipitationAdvertised + ADVERTISE_DELAY:
            print("Readvertising Precipitation sensor")
            publishPrecipitationSensor(mqtt_client)
            lastPrecipitationAdvertised = time.monotonic()
        precipitationVal = precipitationIn.value
        if precipitationVal != lastPrecipitationIn:
            if not precipitationPublished:
                publishPrecipitationSensor(mqtt_client)
                precipitationPublished = True
            lastPrecipitationIn = precipitationVal
            rainCount += 1
            print(rainCount)
            output = {
                "precipitation": rainCount / 3.467}
            mqtt_client.publish(getTopic("precipitation"), json.dumps(output))
        if precipitationPublished and time.monotonic() > lastPrecipitationUpdate + UPDATE_DELAY:
            output = {
                "precipitation": rainCount / 3.467}
            mqtt_client.publish(getTopic("precipitation"), json.dumps(output))
            lastPrecipitationUpdate = time.monotonic()
    return precipitationIn, lastPrecipitationUpdate, lastPrecipitationAdvertised, precipitationPublished, rainCount, lastPrecipitationIn

def runOccupancy(occupancyIn, lastOccupancyUpdate: int, lastOccupancyAdvertised: int, occupancyPublished: bool, lastOccupancyValue: bool, mqtt_client: MQTT.MQTT):
    if not occupancyPublished:
        if occupancyIn is None:
            # Initialize occupancy sensor
            print("Initializing Occupancy Sensor")
            _, occupancyIn = initOccupancy()
            if occupancyIn is not None:
                lastOccupancyValue = occupancyIn.value
        elif lastOccupancyValue != occupancyIn.value:
            # Occupancy sensor detected a change, indicating the sensor is hooked up
            print("Decteded first change of Occupancy sensor, starting advertising!")
            publishOccupancySensor(mqtt_client)
            occupancyPublished = True
    if occupancyPublished and time.monotonic() > lastOccupancyAdvertised + ADVERTISE_DELAY:
        # Advertise rain drop sensor with autodiscovery periodically
        print("Readvertising occupancy sensor")
        publishOccupancySensor(mqtt_client)
        lastOccupancyAdvertised = time.monotonic()
    if occupancyPublished and time.monotonic() > lastOccupancyUpdate + UPDATE_DELAY:
        # Do regular update of rain drop sensor value
        print(occupancyOutput(occupancyIn))
        mqtt_client.publish(getBinaryTopic("occupancy"), occupancyOutput(occupancyIn))
        lastOccupancyUpdate = time.monotonic()
    return occupancyIn, lastOccupancyUpdate, lastOccupancyAdvertised, occupancyPublished, lastOccupancyValue
        

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
    state_topic = "homeassistant/sensor/temperature/state"
    lastbmeupdate = 0
    lastbmeadvertised = 0
    lastPrecipitationIn = precipitationIn.value
    lastdropupdate = 0
    lastdropadvertised = 0
    dropDIn = None
    rainCount = 0
    precipitationPublished = False
    lastPrecipitationUpdate = 0
    lastPrecipitationAdvertised = 0
    dropPublished = False
    lastDropValue = None
    occupancyIn = None
    lastOccupancyUpdate = 0
    lastOccupancyAdvertised = 0
    lastOccupancyValue = True
    occupancyPublished = False

    _, bme = initBme()
    while True:
        bme, lastbmeupdate, lastbmeadvertised = runBME(bme, lastbmeupdate, lastbmeadvertised, mqtt_client)
        dropDIn, lastdropupdate, lastdropadvertised, lastDropValue, dropPublished = runDrop(dropDIn, lastdropupdate, lastdropadvertised, lastDropValue, dropPublished, mqtt_client)
        precipitationIn, lastPrecipitationUpdate, lastPrecipitationAdvertised, precipitationPublished, rainCount, lastPrecipitationIn = runPrecipitation(precipitationIn, lastPrecipitationUpdate, lastPrecipitationAdvertised, precipitationPublished, rainCount, lastPrecipitationIn, mqtt_client)
        occupancyIn, lastOccupancyUpdate, lastOccupancyAdvertised, occupancyPublished, lastOccupancyValue = runOccupancy(occupancyIn, lastOccupancyUpdate, lastOccupancyAdvertised, occupancyPublished, lastOccupancyValue, mqtt_client)
        time.sleep(SWITCH_DELAY)
run()
# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython Essentials UART Serial example"""
"""import time
import board
#import inspect
#import pydoc
import busio
import digitalio
from analogio import AnalogIn"""

#analogIn = AnalogIn(board.A0)

# For most CircuitPython boards:
"""inPin = digitalio.DigitalInOut(board.A0)
inPin.direction = digitalio.Direction.INPUT
inPin.pull = digitalio.Pull.DOWN"""
# For QT Py M0:
# led = digitalio.DigitalInOut(board.SCK)
#led.direction = digitalio.Direction.OUTPUT

#uart = busio.UART(board.TX, board.RX, baudrate=115200, bits=8)
"""data = uart.read(256)
uart.write(b"get_all\r\n")
uart.write(b"th1=1200\r\n")
uart.write(b"th2=2500\r\n")
uart.write(b"get_all\r\n")
print(data.decode("ascii").strip())"""
"""while True:
    print(inPin.value)
    #time.sleep(0.1)
    #data = uart.read(64)  # read up to 32 bytes
    data = uart.readline()
    # print(data)  # this is a bytearray type
    print(data.decode("ascii").strip())

"""