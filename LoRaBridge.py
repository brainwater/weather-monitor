import board
import busio
import digitalio
import time
import ssl
import wifi
import json
import socketpool
import neopixel
import traceback
import gc
import adafruit_ntp
import adafruit_rfm9x
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# I'm getting about 400ft of range with LoRa

EXPIRE_DELAY = 60*75*3

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.fill((20, 0, 0))

def showFinish():
    while True:
        pixel.fill((0, 255, 0))
        time.sleep(0.5)
        pixel.fill((0, 0, 0))
        time.sleep(0.5)
def showError():
    while True:
        pixel.fill((255, 0, 0))
        time.sleep(0.5)
        pixel.fill((0, 0, 0))
        time.sleep(0.5)
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    showError()
    raise

def initMqtt():
    try:
        if not isWifiConnected():
            print("Wifi not connected, cannot connect mqtt!")
            return None
        print("Initializing Mqtt")
        # Create a socket pool
        pool = socketpool.SocketPool(wifi.radio)
        # Set up a MiniMQTT Client
        mqtt_client = MQTT.MQTT(
            broker=secrets["mqtt_broker"],
            port=secrets["mqtt_port"],
            username=secrets["mqtt_username"],
            password=secrets["mqtt_password"],
            socket_pool=pool,
            ssl_context=ssl.create_default_context(),
        )
        print("Attempting to connect to %s" % mqtt_client.broker)
        mqtt_client.connect()
        return mqtt_client
    except Exception as ex:
        print(ex)
        mqtt_client = None
        return None

def isWifiConnected():
    return wifi.radio.connected

def connectWifi():
    print("Checking/connecting wifi")
    print("Attempting to connect")
    #try:
    #    wifi.radio.connect(secrets['ssid'], secrets['password'])
    #except Exception as ex:
    #    pixel.fill((50,0,0))
    #    print(ex)
    while not isWifiConnected():
        pixel.fill((50,0,0))
        try:
            wifi.radio.connect(secrets['ssid'], secrets['password'])
        except Exception as ex:
            print(ex)
            time.sleep(0.5)
    if wifi.radio.connected:
        print("Connection successful!")

def mqttConnected(mqtt_client):
    if not wifi.radio.connected:
        return False
    try:
        resp = mqtt_client.ping()
    except MQTT.MMQTTException as ex:
        print(ex)
        print("MQTTException when pinging server!")
        return False
    return mqtt_client.is_connected()

def initRfm():
    # Define radio parameters.
    RADIO_FREQ_MHZ = 915.0  # Frequency of the radio in Mhz. Must match your
    # module! Can be a value like 915.0, 433.0, etc.
    # Define pins connected to the chip, use these if wiring up the breakout according to the guide:
    CS = digitalio.DigitalInOut(board.A3)
    RESET = digitalio.DigitalInOut(board.A2)
    # Initialize SPI bus.
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    # Initialze RFM radio
    rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

    # Note that the radio is configured in LoRa mode so you can't control sync
    # word, encryption, frequency deviation, or other settings!

    # You can however adjust the transmit power (in dB).  The default is 13 dB but
    # high power radios like the RFM95 can go up to 23 dB:
    rfm9x.tx_power = 23
    rfm9x.coding_rate = 7
    rfm9x.spreading_factor = 9
    rfm9x.node = 255
    #rfm9x.agc = True
    #rfm9x.enable_crc = False
    #rfm9x.preamble_length
    return rfm9x

def batteryADCToVolts(adc):
    # One example reading was 2.99 V with a reading of 929
    # One example with a full battery was 935
    return int(adc) * 2.99 / 950

def batteryADCToPercent(adc):
    # Use 1.5V as the full alkaline battery value (so 3V with 2 batteries)
    # Use 1V as the empty alkaline battery value (so 2V with 2 batteries)
    minVolt = 2.0
    maxVolt = 3.0
    spread = maxVolt - minVolt
    volts = batteryADCToVolts(adc)
    batteryRatio = (volts - minVolt) / spread
    return 100 * batteryRatio

def soilMoistureADCToPercent(adc):
    # The higher the adc value, the less moisture.
    # Max ADC value in air was 887
    # Min ADC value in water was 520, or when I dunked it way past the line in water it was 480
    minVal = 500.0
    maxVal = 900.0
    spread = maxVal - minVal
    ratioMoist = (maxVal - int(adc)) / spread
    percentMoisture = 100.0 * ratioMoist
    return percentMoisture

def getTopic(sensorType, prefix, postfix="/state"):
    return "homeassistant/sensor/" + prefix + sensorType + postfix

def advertise_and_publish(mqtt_client, data):
    if data is None:
        print("Empty data!")
        return False
    id = data["id"]
    prefix = "lora_soil_" + str(id) + "_sensor_"
    name_prefix = "LoRa Soil " + str(id) + " "
    sensors = [
        {"class": "temperature", "name": "Temperature", "unit": "°C"},
        {"class": "humidity", "name": "Humidity", "unit": "%rH"},
        {"class": "battery", "name": "Battery", "unit": "%"},
        {"class": "moisture", "name": "Soil Moisture", "unit": "%"},
        {"class": "temperature", "name": "Temperature", "unit": "°C"},
        {"class": "signal_strength", "name": "Signal Strength", "unit": "dB"},
    ]
    for sensor in sensors:
        sensorname = sensor["class"]
        topic = getTopic(sensorname, prefix, "/config")
        payload = {
            "name": name_prefix + sensor["name"],
            "device_class": sensorname,
            "state_topic": getTopic(sensorname, prefix),
            "unit_of_measurement": sensor["unit"],
            "expire_after": EXPIRE_DELAY,
            "unique_id": prefix + sensorname,
            "suggested_display_precision": "1",
            "value_template": "{{ value_json." + sensorname + " | round(1) }}"}
        mqtt_client.publish(topic, json.dumps(payload))
        

    # Add delay so home assistant can register the sensors on first startup
    time.sleep(0.1)
    for sensor in ["temperature", "humidity", "battery", "moisture", "signal_strength"]:
        topic = getTopic(sensor, prefix)
        mqtt_client.publish(topic, json.dumps(data))
    return True

def parseSensor(input: bytes) -> dict:
    text = str(input, "utf-8")
    space_split = text.split(" ")
    id = space_split[0]
    hum = space_split[5]
    temp = space_split[6]
    moisture = space_split[7]
    batt = space_split[8]
    print(space_split)
    assert(hum.startswith("H:"))
    assert(temp.startswith("T:"))
    assert(moisture.startswith("ADC:"))
    assert(batt.startswith("BAT:"))
    return {
        "id": id,
        "temperature": float(temp[2:]),
        "humidity": float(hum[2:]),
        "moisture": soilMoistureADCToPercent(moisture[4:]),
        "battery": batteryADCToPercent(batt[4:]),
    }
def main():
    while True:
        try:
            outerLoop()
        except Exception as ex:
            print("Error when running outer loop!")
            print(ex)
            print(traceback.format_exception(ex))
        gc.collect() # Try to uninitialize the mqtt client and rfm9x

def outerLoop():
    connectWifi()
    rfm9x = initRfm()
    mqtt_client = initMqtt()
    pixel.fill((0,0,0))
    print("Waiting for packets...")
    while True:
        try:
            innerLoop(mqtt_client=mqtt_client, rfm9x=rfm9x)
        except Exception as ex:
            print("Error when running inner loop!")
            print(ex)
            print(traceback.format_exception(ex))

def innerLoop(mqtt_client, rfm9x):
    packet = rfm9x.receive(timeout=60.0)
    #now = ntp.datetime
    #print(str(now.tm_hour) + ":" + str(now.tm_min) + ":" + str(now.tm_sec))
    if packet is None:
        # Packet has not been received
        print("Received nothing! Listening again...")
    else:
        # Received a packet!
        # Print out the raw bytes of the packet:
        print("Received (raw bytes): {0}".format(packet))
        # And decode to UTF-8 text and print it too.
        packet_text = str(packet, "utf-8")
        print("Received (UTF-8): {0}".format(packet_text))
        # Also read the RSSI (signal strength) of the last received message and
        # print it.
        rssi = rfm9x.last_rssi
        print("Received signal strength: {0} dB".format(rssi))
        try:
            packet_data = parseSensor(packet)
            packet_data['signal_strength'] = rssi
            print(packet_data)
            mqtt_client.reconnect()
            try:
                advertise_and_publish(mqtt_client, packet_data)
            except OSError:
                pass
        except Exception as ex:
            print("Error when parsing ")
            print(ex)
main()
