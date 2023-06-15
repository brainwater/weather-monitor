import asyncio
import board
import digitalio
import json
from sensorloop import SensorLoop
from secrets import secrets

class PrecipitationSensorLoop(SensorLoop):
    precipitationIn = None
    precipitationCount = 0
    
    async def watchPrecipitationSensor(self):
        while True:
            lastPrecipitation = self.precipitationIn.value
            while lastPrecipitation == self.precipitationIn.value:
                await asyncio.sleep(self.SWITCH_DELAY)
            self.precipitationCount += 1

    async def background(self):
        await self.watchPrecipitationSensor()
    
    async def initSensor(self):
        while self.precipitationIn is None:
            try:
                self.precipitationIn = digitalio.DigitalInOut(self.config['pin'])
                self.precipitationIn.direction = digitalio.Direction.INPUT
                self.precipitationIn.pull = digitalio.Pull.UP
            except Exception as ex:
                print("Error initializing Precipitation sensor!")
                print(ex)
                self.precipitationIn = None
                await asyncio.sleep(self.INIT_DELAY)
        print("Initialized Precipitation Sensor")
        # Wait until we have a change in the precipitation sensor before continuing
        precipitationValue = self.precipitationIn.value
        while precipitationValue == self.precipitationIn.value:
            await asyncio.sleep(self.SWITCH_DELAY)
        print("Detected first change on precipitation sensor")
    
    def advertiseSensor(self):
        topic = self.getTopic("precipitation", "/config")
        payload = {
            "name": secrets['name_prefix'] + "Precipitation",
            "device_class": "precipitation",
            "state_topic": self.getTopic("precipitation"),
            "unit_of_measurement": "mm",
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": secrets['topic_prefix'] + "raingauge",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.precipitation | round(1) }}"}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        print("Sending Precipiation Value")
        output = {
            "precipitation": self.precipitationCount / 3.467}
        self.mqtt_client.publish(self.getTopic("precipitation"), json.dumps(output))
        print("Sent Precipiation Value")

