import serial
import time
import json
import sys
import signal
from sense_hat import SenseHat
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder
from vcgencmd import Vcgencmd

# IoT Core Stuff
ENDPOINT = "a1qecpjelyfwp0-ats.iot.us-east-1.amazonaws.com"
CLIENT_ID = "ntecpi"
PATH_TO_CERT = "/home/pi/code/ntec364-eagles/client/cert/7752c08c83-certificate.pem.crt"
PATH_TO_KEY = "/home/pi/code/ntec364-eagles/client/cert/7752c08c83-private.pem.key"
PATH_TO_ROOT = "/home/pi/code/ntec364-eagles/client/cert/AmazonRootCA1.pem"
TOPIC = "ntecpi/env"

# script stuff
senseHat = None
airSerial = None
mqtt_connection = None
vcgm = Vcgencmd()
calibrateTemp = False

# Should we attempt to calibrate our temps?
try:
    serialDevice = serial.Serial('/dev/ttyUSB1')
    calibrateTemp = serialDevice
except Exception:
    print("Skipping calibration setup.")

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
    print(Exception.with_traceback())
    exit


def getAQ(airSerial):
    data = []
    for index in range(0, 10):
        serIn = airSerial.read()
        data.append(serIn)

    pmTwoFive = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
    pmTen = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10

    return [pmTwoFive, pmTen]


def getCalibrationTemp(calibrateTemp):
    if calibrateTemp is False:
        return
    calibrateTemp.flushInput()
    line = calibrateTemp.readline()
    tempobj = json.loads(line)
    return float(tempobj["degC"])


def getTemp(senseHat):
    cpu_tempc = vcgm.measure_temp()
    temp = senseHat.temperature
    humid = senseHat.get_temperature_from_humidity()
    pressure = senseHat.get_temperature_from_pressure()
    avg = (temp + humid + pressure) / 3
    secondary = False

    try:
        secondary = getCalibrationTemp(calibrateTemp)
    except Exception:
        print("Unable to fetch secondary temperature, skipping")

    calibrated = avg - ((cpu_tempc - avg)/5.466)
    return [temp, humid, pressure, calibrated, avg, secondary]


def getPressure(senseHat):
    return senseHat.get_pressure()


def getHumidity(senseHat):
    return senseHat.get_humidity()


def sendIt(data):
    message = data
    message["timestamp"] = time.time()
    message["source"] = "ntecpiv1"
    try:
        mqtt_connection.publish(
            topic=TOPIC,
            payload=json.dumps(message),
            qos=mqtt.QoS.AT_LEAST_ONCE)
    except Exception:
        print("Unable to publish message, message:", json.dumps(message))


def main():
    global pressureHigh
    while True:
        try:
            AQ = getAQ(airSerial)
            temp = getTemp(senseHat)
            pressure = getPressure(senseHat)
            humidity = getHumidity(senseHat)
            output = {
                    'pm25': AQ[0],
                    'pm10': AQ[1],
                    'tempC': temp[0],
                    'tempCPumid': temp[1],
                    'tempCPressure': temp[2],
                    'tempAvg': temp[4],
                    'tempCalibrated': temp[3],
                    'tempSecondary': temp[5],
                    'pressureMb': pressure,
                    'humidityPct': humidity
                    }
            sendIt(output)
            panelDisplay(output)
            time.sleep(30)
        except KeyboardInterrupt:
            print("Manual kill.")
            cleanup()


def cleanup(*args):
    print("Cleaning up.")
    senseHat.clear()
    sys.exit()


def panelDisplay(data):
    senseHat.set_rotation(180, True)
    # Work on humidity %
    humidLights = int((data["humidityPct"] / (100/8)))

    # Sensor goes from 260 - 1260, 125 per step
    pressureLights = int((data["pressureMb"] - 260) / 125)

    # Set some colors
    humidColor = (0, 0, 255)
    pressureColor = (128, 128, 128)

    # Work on humidity lights
    for pixel in range(0, humidLights):
        senseHat.set_pixel(pixel, 0, humidColor)
    # Work on pressure lights
    for pixel in range(0, pressureLights):
        senseHat.set_pixel(pixel, 1, pressureColor)

    # Work on AQ lights for pm25
    if data["pm25"] > 500:
        senseHat.set_pixel(7, 2, (118, 12, 37))
    if data["pm25"] > 350.4:
        senseHat.set_pixel(6, 2, (118, 12, 37))
    if data["pm25"] > 250.4:
        senseHat.set_pixel(5, 2, (118, 12, 37))
    if data["pm25"] > 150.4:
        senseHat.set_pixel(4, 2, (144, 20, 77))
    if data["pm25"] > 55.4:
        senseHat.set_pixel(3, 2, (240, 33, 23))
    if data["pm25"] > 35.4:
        senseHat.set_pixel(2, 2, (243, 128, 35))
    if data["pm25"] > 12:
        senseHat.set_pixel(1, 2, (254, 250, 61))
    if data["pm25"] > 0:
        senseHat.set_pixel(0, 2, (87, 221, 47))

    # Work on AQ lights for pm10
    if data["pm10"] > 500:
        senseHat.set_pixel(7, 3, (118, 12, 37))
    if data["pm10"] > 350.4:
        senseHat.set_pixel(6, 3, (118, 12, 37))
    if data["pm10"] > 250.4:
        senseHat.set_pixel(5, 3, (118, 12, 37))
    if data["pm10"] > 150.4:
        senseHat.set_pixel(4, 3, (144, 20, 77))
    if data["pm10"] > 55.4:
        senseHat.set_pixel(3, 3, (240, 33, 23))
    if data["pm10"] > 35.4:
        senseHat.set_pixel(2, 3, (243, 128, 35))
    if data["pm10"] > 12:
        senseHat.set_pixel(1, 3, (254, 250, 61))
    if data["pm10"] > 0:
        senseHat.set_pixel(0, 3, (87, 221, 47))

    # SenseHat goes from -40C - 120C
    if data["tempAvg"] > -20:
        senseHat.set_pixel(0, 4, (0, 0, 255))
    if data["tempAvg"] > -10:
        senseHat.set_pixel(1, 4, (0, 64, 128))
    if data["tempAvg"] > 0:
        senseHat.set_pixel(2, 4, (0, 128, 64))
    if data["tempAvg"] > 20:
        senseHat.set_pixel(3, 4, (0, 255, 0))
    if data["tempAvg"] > 40:
        senseHat.set_pixel(4, 4, (0, 255, 0))
    if data["tempAvg"] > 60:
        senseHat.set_pixel(5, 4, (64, 128, 0))
    if data["tempAvg"] > 80:
        senseHat.set_pixel(6, 4, (128, 64, 0))
    if data["tempAvg"] > 100:
        senseHat.set_pixel(7, 4, (255, 0, 0))


# Signal handling
signal.signal(signal.SIGTERM, cleanup)

main()
