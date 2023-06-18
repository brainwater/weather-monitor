import asyncio
import board
import json
from adafruit_max1704x import MAX17048
from sensorloop import SensorLoop
from secrets import secrets

class BatteryLevelLoop(SensorLoop):
    sensor = None
    async def initSensor(self):
        while self.sensor is None:
            try:
                print("Initializing Battery Level")
                i2c = board.STEMMA_I2C()
                self.sensor = MAX17048(i2c)
            except Exception as ex:
                print("Error initializing Bettery Level Sensor")
                print(ex)
                self.sensor = None
                await asyncio.sleep(self.INIT_DELAY)
    
    def advertiseSensor(self):
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
            "value_template": "{{ value_json.battery | round(1) }}"}
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
            "unique_id": prefix + "batterygauge",
            "suggested_display_precision": "2",
            "value_template": "{{ value_json.batteryvoltage }}"}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        battery = self.sensor.cell_percent
        batteryvoltage = self.sensor.cell_voltage
        print(f"Battery voltage: {self.sensor.cell_voltage:.2f} Volts")
        print(f"Battery state  : {self.sensor.cell_percent:.1f} %")
        output = {
            "battery": battery}
        self.mqtt_client.publish(self.getTopic("battery"), json.dumps(output))
        output = {
            "batteryvoltage":  batteryvoltage}
        self.mqtt_client.publish(self.getTopic("batteryvoltage"), json.dumps(output))
        print("Published Battery Value")

