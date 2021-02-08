import serial
import time
import json
import sys
from sense_hat import SenseHat
from awscrt import io, mqtt, auth
from awsiot import mqtt_connection_builder

# IoT Core Stuff
ENDPOINT = "a1qecpjelyfwp0-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "ntecpi"
PATH_TO_CERT = "cert/7752c08c83-certificate.pem.crt"
PATH_TO_KEY = "cert/7752c08c83-private.pem.key"
PATH_TO_ROOT = "cert/AmazonRootCA1.pem"
TOPIC = "ntecpi/env"

# script stuff
senseHat = None
airSerial = None
pressureHigh = 1
mqtt_connection = None

# Initial sensor setup, always happens.
try:
    senseHat = SenseHat()
except Exception:
    print("Problem loading SenseHat, aborting.")
    exit

try:
    airSerial = serial.Serial('/dev/ttyUSB0')
except Exception:
    print("Problem connecting to AQ sensor, aborting!")
    exit

try:
    print("Starting MQTT Connection process...")
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=PATH_TO_CERT,
            pri_key_filepath=PATH_TO_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_ROOT,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=6)
    # Make the connect() call
    connect_future = mqtt_connection.connect()
    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")
    # Publish message to server desired number of times.
except Exception:
    print("Problem connecting, aborting.")
    exit


def getAQ(airSerial):
    data = []
    for index in range(0, 10):
        serIn = airSerial.read()
        data.append(serIn)

    pmTwoFive = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
    pmTen = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10

    return [pmTwoFive, pmTen]


def getTemp(senseHat):
    temp = senseHat.temperature
    humid = senseHat.get_temperature_from_humidity()
    pressure = senseHat.get_temperature_from_pressure()
    avg = (temp + humid + pressure) / 3
    return [temp, humid, pressure, avg]


def getPressure(senseHat):
    return senseHat.get_pressure()


def getHumidity(senseHat):
    return senseHat.get_humidity()


def sendIt(data):
    message = {"message": data, "timestamp": time.time(), "source": "ntecpiv1"}
    mqtt_connection.publish(
            topic=TOPIC,
            payload=json.dumps(message),
            qos=mqtt.QoS.AT_LEAST_ONCE)
    print("Sent: ", json.dumps(message))


def main():
    global pressureHigh
    while True:
        try:
            AQ = getAQ(airSerial)
            temp = getTemp(senseHat)
            pressure = getPressure(senseHat)
            if (pressure > pressureHigh):
                pressureHigh = pressure
            humidity = getHumidity(senseHat)
            output = {
                    'pm25': AQ[0],
                    'pm10': AQ[1],
                    'tempC': temp[0],
                    'tempCPumid': temp[1],
                    'tempCPressure': temp[2],
                    'tempAvg': temp[3],
                    'pressureMb': pressure,
                    'humidityPct': humidity
                    }
            sendIt(output)
            panelDisplay(output)
            time.sleep(10)
        except KeyboardInterrupt:
            print("Cleaning up.")
            senseHat.clear()
            sys.exit()

def panelDisplay(data):
    senseHat.set_rotation(180,True)
    # Work on humidity %
    humidLights = int((data["humidityPct"] / (100/8)))
    pressureLights = int((data["pressureMb"] / (pressureHigh/8)))
    humidColor = (0, 0, 255)
    pressureColor = (128, 128, 128)
    for pixel in range(0, humidLights):
        senseHat.set_pixel(pixel, 0, humidColor)
    for pixel in range(0, pressureLights):
        senseHat.set_pixel(pixel, 1, pressureColor)

    if data["pm25"] > 500:
        senseHat.set_pixel(7, 2, (118, 12, 37))
    if data["pm25"] > 400:
        senseHat.set_pixel(6, 2, (118, 12, 37))
    if data["pm25"] > 300:
        senseHat.set_pixel(5, 2, (118, 12, 37))
    if data["pm25"] > 200:
        senseHat.set_pixel(4, 2, (144, 20, 77))
    if data["pm25"] > 150:
        senseHat.set_pixel(3, 2, (240, 33, 23))
    if data["pm25"] > 100:
        senseHat.set_pixel(2, 2, (243, 128, 35))
    if data["pm25"] > 50:
        senseHat.set_pixel(1, 2, (254, 250, 61))
    if data["pm25"] > 0:
        senseHat.set_pixel(0, 2, (87, 221, 47))


main()
