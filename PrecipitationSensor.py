import asyncio
import sys
import alarm
import board
import digitalio
import json
from Sensor import Sensor
from secrets import secrets

class PrecipitationSensor(Sensor):
    precipitationIn = None
    #precipitationCount = 0
    backgroundTask = None
    
    async def watchPrecipitationSensor(self):
        while True:
            lastPrecipitation = self.precipitationIn.value
            while lastPrecipitation == self.precipitationIn.value:
                await asyncio.sleep(self.SWITCH_DELAY)
            lastPrecipitation = self.precipitationIn.value
            self.incrementCount()
            # Avoid detecting bounces
            await asyncio.sleep(0.2)

    async def alarms(self):
        # We must release the pin before we can create the alarm
        if self.backgroundTask is not None:
            self.backgroundTask.cancel()
            try:
                await self.backgroundTask
            except:
                # Cancelled task throws an exception/error
                pass
        self.precipitationIn.deinit()
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

    async def init(self):
        print("Initializing Precipitation Sensor")
        if (alarm.wake_alarm is not None) and isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
            # Increment by 2 since the count is the count of the changes in pin state, with sleep we're only counting when it goes low
            self.incrementCount()
            self.incrementCount()

        try:
            self.precipitationIn = digitalio.DigitalInOut(self.config['pin'])
            self.precipitationIn.direction = digitalio.Direction.INPUT
            self.precipitationIn.pull = digitalio.Pull.UP
            print("Initialized Precipitation Sensor")
            # Wait until we have a change in the precipitation sensor before continuing
            self.backgroundTask = asyncio.create_task(self.watchPrecipitationSensor())
        except Exception as ex:
            print("Error initializing Precipitation sensor!")
            print(ex)
            self.precipitationIn = None
        
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
            "value_template": "{{ value_json.precipitation | round(1) }}",
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def sendValue(self):
        print("Sending Precipiation Value")
        output = {
            "precipitation": self.countFromMemory() / 3.467}
        print(output)
        self.mqtt_client.publish(self.getTopic("precipitation"), json.dumps(output), qos=1)
        print("Sent Precipiation Value")

