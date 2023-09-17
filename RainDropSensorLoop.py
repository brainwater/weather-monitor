import asyncio
import board
import digitalio
import json
from adafruit_bme280 import basic as adafruit_bme280
from sensorloop import SensorLoop
from secrets import secrets
import traceback

class RainDropSensorLoop(SensorLoop):
    dropDIn = None
    
    def getTopic(self, sensorType, postfix="/state"):
        return "homeassistant/binary_sensor/" + secrets["topic_prefix"] + sensorType + postfix
    
    def isRaining(self):
        try:
            return not self.dropDIn.value
        except Exception as ex:
            print("Problem with raining")
            raise ex

    def rainDropOutput(self):
        try:
            if self.isRaining():
                output = {"state": "ON"}
            else:
                output = {"state": "OFF"}
        except Exception as ex:
            print("Problem with if statement")
            raise ex
        return json.dumps(output)

    def singleInitSensor(self):
        print("Intializing Rain Drop Sensor")
        self.dropDIn = digitalio.DigitalInOut(self.config['pin'])
        self.dropDIn.direction = digitalio.Direction.INPUT
        self.dropDIn.pull = digitalio.Pull.UP
    async def initSensor(self):
        while self.dropDIn is None:
            try:
                self.singleInitSensor()
            except Exception as ex:
                print("Error initializing Rain Drop sensor!")
                print(ex)
                self.dropDIn = None
                await asyncio.sleep(self.INIT_DELAY)
        print("Initialized Rain Drop Sensor")
        # Wait until we have a change in the rain sensor before continuing
        initialValue = self.isRaining()
        while initialValue == self.isRaining():
            await asyncio.sleep(self.UPDATE_DELAY)
        print("Detected first change on Rain Drop Sensor")
    
    def advertiseSensor(self):
        topic = self.getTopic("rain_drop", "/config")
        payload = {
            "name": secrets['name_prefix'] + "Rain Drop",
            "device_class": "moisture",
            "state_topic": self.getTopic("rain_drop"),
            "payload_available": "online",
            "payload_not_available": "offline",
            "expire_after": self.EXPIRE_DELAY,
            "unique_id": secrets['topic_prefix'] + "raindropsensor",
            "value_template": "{{ value_json.state }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        topic = self.getTopic("rain_drop")
        output = self.rainDropOutput()
        self.mqtt_client.publish(topic, output, qos=1)
        print("Sent Rain Drop Value")

