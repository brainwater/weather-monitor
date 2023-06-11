import asyncio
import board
import json
from adafruit_bme280 import basic as adafruit_bme280
from sensorloop import SensorLoop
from secrets import secrets

class BMESensorLoop(SensorLoop):
    bme = None
    async def initSensor(self):
        while self.bme is None:
            try:
                print("Initializing BME")
                i2c = board.STEMMA_I2C()
                bme = adafruit_bme280.Adafruit_BME280_I2C(i2c)
                bme.mode = adafruit_bme280.MODE_SLEEP
                self.bme = bme
            except Exception as ex:
                print("Error initializing BME Sensor")
                print(ex)
                self.bme = None
                await asyncio.sleep(self.INIT_DELAY)
    
    def advertiseSensor(self):
        topic = self.getTopic("temperature", "/config")
        prefix = secrets['topic_prefix']
        name_prefix = secrets['name_prefix']
        payload = {
            "name": name_prefix + "Temperature",
            "device_class": "temperature",
            "state_topic": self.getTopic("temperature"),
            "unit_of_measurement": "°C",
            "expire_after": self.EXPIRE_DELAY,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": prefix + "temperaturegauge",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.temperature | round(1) }}"}
        self.mqtt_client.publish(topic, json.dumps(payload))
        topic = self.getTopic("humidity", "/config")
        payload = {
            "name": name_prefix + "Humidity",
            "device_class": "humidity",
            "state_topic": self.getTopic("humidity"),
            "unit_of_measurement": "%rH",
            "expire_after": self.EXPIRE_DELAY,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": prefix + "humiditygauge",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.humidity | round(1) }}"}
        self.mqtt_client.publish(topic, json.dumps(payload))
        topic = self.getTopic("pressure", "/config")
        payload = {
            "name": name_prefix + "Pressure",
            "device_class": "pressure",
            "state_topic": self.getTopic("pressure"),
            "unit_of_measurement": "hPa",
            "expire_after": self.EXPIRE_DELAY,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": prefix + "pressuregauge",
            "suggested_display_precision": "1",
            "value_template": "{{ value_json.pressure | round(1) }}"}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        temperature = self.bme.temperature
        relative_humidity = self.bme.relative_humidity
        pressure = self.bme.pressure
        output = {
            "temperature": temperature}
        self.mqtt_client.publish(self.getTopic("temperature"), json.dumps(output))
        output = {
            "humidity": relative_humidity}
        self.mqtt_client.publish(self.getTopic("humidity"), json.dumps(output))
        output = {
            "pressure": pressure}
        self.mqtt_client.publish(self.getTopic("pressure"), json.dumps(output))
        print("Published BME Values")

