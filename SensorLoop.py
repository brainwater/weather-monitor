import asyncio
from secrets import secrets

class SensorLoop:
    INIT_DELAY = 60
    SWITCH_DELAY = 0.05
    UPDATE_DELAY = 60
    ADVERTISE_DELAY = 60
    EXPIRE_DELAY = 5*60
    mqtt_client = None
    config = None
    
    def __init__(self, mqtt_client, config):
        self.mqtt_client = mqtt_client
        self.config = config

    def alarms(self):
        return []

    def singleInitSensor(self):
        raise NotImplemented()
        
    async def initSensor(self):
        raise NotImplemented()
    
    def advertiseSensor(self):
        raise NotImplemented()
    
    def sendValue(self):
        raise NotImplemented()
    
    async def background(self):
        pass
    
    def checkConnection(self) -> bool:
        # TODO: Add a check for the home assistant connection
        return self.mqtt_client.is_connected()

    async def advertiseLoop(self):
        while True:
            if self.checkConnection():
                try:
                    self.advertiseSensor()
                except:
                    print("Error when advertising sensor!")
            else:
                print("Disconnected! Skipping advertise.")
            await asyncio.sleep(self.ADVERTISE_DELAY)
    
    async def sendValueLoop(self):
        while True:
            if self.checkConnection():
                try:
                    self.sendValue()
                except:
                    print("Error when sending value for sensor!")
            else:
                print("Disconnected! Skipping sendValue.")
            await asyncio.sleep(self.UPDATE_DELAY)
    
    async def run(self):
        await self.initSensor()
        asyncio.create_task(self.background())
        await asyncio.gather(
            self.advertiseLoop(),
            self.sendValueLoop(),
            return_exceptions=True)

    def singleRun(self):
        self.singleInitSensor()
        self.advertiseSensor()
        self.sendValue()

    def getTopic(self, sensorType, postfix="/state"):
        return "homeassistant/sensor/" + secrets["topic_prefix"] + sensorType + postfix
