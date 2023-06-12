import asyncio
from secrets import secrets

class SensorLoop:
    INIT_DELAY = 60
    SWITCH_DELAY = 0.05
    UPDATE_DELAY = 20
    ADVERTISE_DELAY = 60
    EXPIRE_DELAY = 5*60
    mqtt_client = None
    config = None
    
    def __init__(self, mqtt_client, config):
        self.mqtt_client = mqtt_client
        self.config = config

    async def initSensor(self):
        raise NotImplemented()
    
    async def advertiseSensor(self):
        raise NotImplemented()
    
    async def sendValue(self):
        raise NotImplemented()
    
    async def background(self):
        pass
    
    # TODO: Make this exit if the sendBMEValue loop exits, so we can refresh bme
    async def advertiseLoop(self):
        while True:
            self.advertiseSensor()
            await asyncio.sleep(self.ADVERTISE_DELAY)
    
    async def sendValueLoop(self):
        while True:
            self.sendValue()
            await asyncio.sleep(self.UPDATE_DELAY)
    
    async def run(self):
        await self.initSensor()
        asyncio.create_task(self.background())
        await asyncio.gather(
            self.advertiseLoop(),
            self.sendValueLoop(),
            return_exceptions=True)

    def getTopic(self, sensorType, postfix="/state"):
        return "homeassistant/sensor/" + secrets["topic_prefix"] + sensorType + postfix
