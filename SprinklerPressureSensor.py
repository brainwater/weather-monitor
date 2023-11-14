import asyncio
import board
import json
import time
import analogio
from Sensor import Sensor
from secrets import secrets

class SprinklerPressureSensor(Sensor):
    inpin = None

    async def init(self):
        print("Initializing Sprinkler Pressure")
        self.inpin = analogio.AnalogIn(self.config['pin'])
    
    def advertiseSensor(self):
        print("Advertising Sprinkler Pressure!")
        prefix = secrets['topic_prefix']
        name_prefix = secrets['name_prefix']
        topic = self.getTopic("sprinklerpressure", "/config")
        payload = {
            "name": name_prefix + "Sprinkler Pressure",
            "device_class": "pressure",
            "state_topic": self.getTopic("sprinklerpressure", "/state"),
            "unit_of_measurement": "psi",
            "expire_after": self.EXPIRE_DELAY,
            "unique_id": prefix + "sprinklerpressuregauge",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.pressure | round(2) }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        # 0.5V for 0 psi
        # 4.5V for 100 psi
        # voltage divider that reduces the voltage by 33%, or sensor is 1.5 times the voltage of the microcontroller inpin pin
        # range goes from 0 - 65535 inclusive
        # Range goes from 0 - 3.3 V
        # TODO: Use another pin to measure and compare against 5V rail for more accuracy
        ivolt = (self.inpin.value / 65535.0) * 3.3 # Voltage on microcontroller input pin
        svolt = ivolt * 1.5 # Voltage on sensor output
        soffset = svolt - 0.5 # Voltage offset from 0.5V
        pressure = (soffset/4.0) * 100 # PSI of sensor
        output = {
            "pressure": pressure}
        self.mqtt_client.publish(self.getTopic("sprinklerpressure", "/state"), json.dumps(output))
        print("Published Sprinkler Pressure Value")

