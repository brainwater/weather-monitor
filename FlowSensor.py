import asyncio
import board
import json
import time
#import microcontroller
#mport adafruit_mprls
import countio
from Sensor import Sensor
from secrets import secrets

class FlowSensor(Sensor):
    counter = None
    count = 0

    async def init(self):
        # TODO: Initialize with previous count to keep consisitent flow between power cycles
        print("Initializing Flow")
        self.counter = countio.Counter(self.config['pin'])
    
    def advertiseSensor(self):
        print("Advertising Flow!")
        prefix = secrets['topic_prefix']
        name_prefix = secrets['name_prefix']
        topic = self.getTopic("sprinklerflow", "/config")
        payload = {
            "name": name_prefix + "Sprinkler Flow Sensor",
            "device_class": "water",
            "state_topic": self.getTopic("sprinklerflow", "/state"),
            "unit_of_measurement": "L",
            "expire_after": self.EXPIRE_DELAY,
            "unique_id": prefix + "sprinklerflow",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.water | round(2) }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        # 12 pulses per liter
        # TODO: Fix case for when self.count overflows at (2^30)-1 or 1073741823, about 6 years of daily use of 10,000 gallons of water would reach this
        # Use separate storage int since the countio overflows somewhere between 32,729 and -32175.
        self.count += self.counter.count
        self.counter.reset()
        output = {
            "water": self.count / 12.0}
        self.mqtt_client.publish(self.getTopic("sprinklerflow", "/state"), json.dumps(output))
        print("Published Sprinkler Flow")

