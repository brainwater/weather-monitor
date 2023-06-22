import asyncio
import sys
import alarm
import board
import digitalio
import json
from sensorloop import SensorLoop
from secrets import secrets

class PrecipitationSensorLoop(SensorLoop):
    precipitationIn = None
    #precipitationCount = 0
    
    async def watchPrecipitationSensor(self):
        while True:
            lastPrecipitation = self.precipitationIn.value
            while lastPrecipitation == self.precipitationIn.value:
                await asyncio.sleep(self.SWITCH_DELAY)
            #self.precipitationCount += 1
            self.incrementCount

    def alarms(self):
        pin_alarm = alarm.pin.PinAlarm(pin=self.config['pin'], value=False, pull=True)
        return [pin_alarm]

    async def background(self):
        await self.watchPrecipitationSensor()

    def incrementCount(self):
        self.saveCount((self.countFromMemory() + 1) % ((2 ** 8) ** 4))
    
    def countFromMemory(self):
        if len(alarm.sleep_memory) < 4:
            return 0
        mem = alarm.sleep_memory[:4]
        return int.from_bytes(mem, sys.byteorder)

    def saveCount(self, count):
        for i, b in enumerate(count.to_bytes(4, sys.byteorder)):
            alarm.sleep_memory[i] = b

    def singleInitSensor(self):
        if alarm.wake_alarm is None:
            return
        if not isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
            return
        # Increment by 2 since the count is the count of the changes in pin state, with sleep we're only counting when it goes low
        self.incrementCount()
        self.incrementCount()
        
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
        asyncio.create_task(self.watchPrecipitationSensor())
    
    def advertiseSensor(self):
        # Don't publish unless we've sensed rain already
        if self.countFromMemory() <= 0:
            return
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
            "precipitation": self.countFromMemory() / 3.467}
        self.mqtt_client.publish(self.getTopic("precipitation"), json.dumps(output), qos=1)
        print("Sent Precipiation Value")

