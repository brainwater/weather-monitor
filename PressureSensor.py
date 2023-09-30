import asyncio
import board
import json
import time
import microcontroller
import adafruit_mprls
from Sensor import Sensor
from secrets import secrets

class PressureSensor(Sensor):
    mprls = None
    ADDRESS = 0x18
    #UID = ''.join(format(x, '02x') for x in microcontroller.cpu.uid)
    #pressure_id = "mprlspressure_" + UID

    async def init(self):
        print("Initializing Pressure")
        i2c = board.I2C()
        # TODO: this can loop forever!
        while not i2c.try_lock():
            print("Waiting on i2c lock!")
            time.sleep(0.1)
        if self.ADDRESS not in i2c.scan():
            i2c.unlock()
            raise Exception("Unable to find i2c device at 0x77 for BME280!")
        else:
            i2c.unlock()
        self.mprls = adafruit_mprls.MPRLS(i2c, psi_min=0, psi_max=25)
    
    def advertiseSensor(self):
        print("Advertising Pressure!")
        prefix = secrets['topic_prefix']
        name_prefix = secrets['name_prefix']
        topic = self.getTopic("mprlspressure", "/config")
        payload = {
            "name": name_prefix + "MPRLS Pressure",
            "device_class": "pressure",
            "state_topic": self.getTopic("mprlspressure", "/state"),
            "unit_of_measurement": "hPa",
            "expire_after": self.EXPIRE_DELAY,
            "unique_id": prefix + "mprlspressuregauge",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.pressure | round(2) }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        pressure = self.mprls.pressure
        output = {
            "pressure": pressure}
        self.mqtt_client.publish(self.getTopic("mprlspressure", "/state"), json.dumps(output))
        print("Published MPRLS Pressure Value")

