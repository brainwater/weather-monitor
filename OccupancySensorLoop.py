import asyncio
import board
import digitalio
import json
from adafruit_bme280 import basic as adafruit_bme280
from sensorloop import SensorLoop
from secrets import secrets

class OccupancySensorLoop(SensorLoop):
    occupancyIn = None
    
    def getTopic(self, sensorType, postfix="/state"):
        return "homeassistant/binary_sensor/" + secrets["topic_prefix"] + sensorType + postfix
    
    def occupancyOutput(self):
        if self.occupancyIn.value:
            output = {"state": "ON"}
        else:
            output = {"state": "OFF"}
        return json.dumps(output)
    
    async def initSensor(self):
        while self.occupancyIn is None:
            try:
                self.occupancyIn = digitalio.DigitalInOut(self.config['pin'])
                self.occupancyIn.direction = digitalio.Direction.INPUT
                self.occupancyIn.pull = digitalio.Pull.DOWN
                # Don't need uart unless I'm getting more detailed info or changing settings
                #uart = busio.UART(board.TX, board.RX, baudrate=115200, bits=8)
            except Exception as ex:
                self.occupancyIn = None
                print("Error initializing occupancy sensor!")
                print(ex)
                await asyncio.sleep(self.INIT_DELAY)
        print("Initialized Occupancy Sensor")
        # Wait until we have a change in the occupancy sensor before continuing
        initialValue = self.occupancyIn.value
        while initialValue == self.occupancyIn.value:
            await asyncio.sleep(self.SWITCH_DELAY)
        print("Detected first change on Occupancy Sensor")
    
    def advertiseSensor(self):
        topic = self.getTopic("occupancy", "/config")
        payload = {
            "name": secrets['name_prefix'] + "Occupancy",
            "device_class": "occupancy",
            "state_topic": self.getTopic("occupancy"),
            "payload_available": "online",
            "payload_not_available": "offline",
            "expire_after": self.EXPIRE_DELAY,
            "unique_id": secrets['topic_prefix'] + "occupancysensor",
            "value_template": "{{ value_json.state }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))    
    
    def sendValue(self):
        self.mqtt_client.publish(self.getTopic("occupancy"), self.occupancyOutput())

