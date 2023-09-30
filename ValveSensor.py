import asyncio
import board
import json
import time
import pwmio
import microcontroller
import adafruit_mprls
from Sensor import Sensor
from secrets import secrets

class ValveSensor(Sensor):
    mprls = None
    ADDRESS = 0x18
    FREQUENCY = 3000
    DUTY_START = 2 ** 16 - 1
    DUTY_ON = 2 ** 12 + 2 ** 10 #+ 2 ** 8 * 2
    valve = None

    def getTopic(self, sensorType, postfix):
        return "homeassistant/switch/" + secrets["topic_prefix"] + sensorType + postfix

    def get_state(self):
        if self.valve is None or self.valve.duty_cycle <= 0:
            return 'OFF'
        else:
            return 'ON'

    def turn_on(self):
        self.valve.duty_cycle = self.DUTY_START
        time.sleep(0.015)
        self.valve.duty_cycle = self.DUTY_ON
        self.sendValue()
        self.is_online()
        print("Turned Valve ON")

    def turn_off(self):
        self.valve.duty_cycle = 0
        self.sendValue()
        self.is_online()
        print("Turned Valve OFF")

    def is_online(self):
        self.mqtt_client.publish(self.getTopic("valve", "/availability"), "online")

    def on_message(self, client, topic, message):
        if topic != self.getTopic("valve", "/command"):
            # Only act when it is the command topic
            return
        if message == 'ON':
            self.turn_on()
        elif message == 'OFF':
            self.turn_off()
        else:
            print("WARNING! Unknown message '{0}' recieved from command topic '{1}'".format(message, topic))

    async def init(self):
        print("Initializing Valve")
        self.valve = pwmio.PWMOut(self.config['pin'], frequency=self.FREQUENCY, duty_cycle=0)

    def advertiseSensor(self):
        print("Advertising Valve!")
        self.mqtt_client.add_topic_callback(self.getTopic("valve", "/command"), lambda client, topic, message: self.on_message(client, topic, message))
        self.mqtt_client.subscribe(self.getTopic("valve", "/command"))
        prefix = secrets['topic_prefix']
        name_prefix = secrets['name_prefix']
        topic = self.getTopic("valve", "/config")
        payload = {
            "name": name_prefix + "Valve",
            "device_class": "switch",
            "expire_after": self.EXPIRE_DELAY,
            "unique_id": prefix + "valveid",
            "state_topic": self.getTopic("valve", "/state"),
            "command_topic": self.getTopic("valve", "/command"),
            "availability": {
                "topic": self.getTopic("valve", "/availability"),
            },
            "device": {
                "name": secrets['name_prefix'],
                "identifiers": secrets['topic_prefix']
            }}
        self.mqtt_client.publish(topic, json.dumps(payload))
        self.is_online()

    
    def sendValue(self):
        self.mqtt_client.publish(self.getTopic("valve", "/state"), self.get_state())
        self.is_online()
        print("Published Valve Value")

