import asyncio
from secrets import secrets

class Sensor:
    INIT_DELAY = 60
    SWITCH_DELAY = 0.02
    UPDATE_DELAY = 60
    ADVERTISE_DELAY = 60
    EXPIRE_DELAY = 5*60
    mqtt_client = None
    config = None
    
    def __init__(self, mqtt_client, config):
        self.mqtt_client = mqtt_client
        self.config = config

    def init(self):
        raise NotImplemented()
    
    def advertise(self):
        raise NotImplemented()
    
    def sendValue(self):
        raise NotImplemented()
    
    def checkConnection(self) -> bool:
        # TODO: Add a check for the home assistant connection
        return self.mqtt_client.is_connected()

    def singleRun(self):
        self.singleInitSensor()
        self.advertiseSensor()
        self.sendValue()

    async def alarms(self):
        return []

    def getTopic(self, sensorType, postfix="/state"):
        return "homeassistant/sensor/" + secrets["topic_prefix"] + sensorType + postfix