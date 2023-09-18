import asyncio
import board
import json
import time
from adafruit_max1704x import MAX17048
from Sensor import Sensor
from secrets import secrets

class BatterySensor(Sensor):
    sensor = None

    async def init(self):
        print("Attempting to initialize Battery Level Sensor")
        i2c = board.I2C()
        # TODO: this can loop forever!
        while not i2c.try_lock():
            print("Waiting on i2c lock!")
            time.sleep(0.1)
        if 0x36 not in i2c.scan():
            i2c.unlock()
            raise Exception("Unable to find i2c device at 0x36 for MAX17048!")
        else:
            i2c.unlock()
        print("Initializing Battery Level")
        self.sensor = MAX17048(i2c)
    
    def advertiseSensor(self):
        print("Advertising battery!")
        if self.sensor is not None:
            print("Sensor not set, skipping advertise")
        topic = self.getTopic("battery", "/config")
        prefix = secrets['topic_prefix']
        name_prefix = secrets['name_prefix']
        payload = {
            "name": name_prefix + "Battery",
            "device_class": "battery",
            "state_topic": self.getTopic("battery"),
            "unit_of_measurement": "%",
            "expire_after": self.EXPIRE_DELAY,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": prefix + "batterygauge",
            "suggested_display_precision": "0",
            "value_template": "{{ value_json.battery | round(1) }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
        topic = self.getTopic("batteryvoltage", "/config")
        payload = {
            "name": name_prefix + "Battery Voltage",
            "device_class": "voltage",
            "state_topic": self.getTopic("batteryvoltage"),
            "unit_of_measurement": "V",
            "expire_after": self.EXPIRE_DELAY,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": prefix + "batteryvoltagegauge",
            "suggested_display_precision": "2",
            "value_template": "{{ value_json.batteryvoltage }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))

    def onWake(self):
        pass

    def sendValue(self):
        if None == self.sensor:
            print("Sensor not set, skipping sendValue")
            return
        battery = self.sensor.cell_percent
        batteryvoltage = self.sensor.cell_voltage
        print(f"Battery voltage: {self.sensor.cell_voltage:.2f} Volts")
        print(f"Battery state  : {self.sensor.cell_percent:.1f} %")
        output = {
            "battery": battery}
        self.mqtt_client.publish(self.getTopic("battery"), json.dumps(output), qos=1)
        output = {
            "batteryvoltage":  batteryvoltage}
        self.mqtt_client.publish(self.getTopic("batteryvoltage"), json.dumps(output), qos=1)
        print("Published Battery Value")
