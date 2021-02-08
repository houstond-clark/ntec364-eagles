import serial
import time
import json
from sense_hat import SenseHat

senseHat = None
airSerial = None

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
    print(json.dumps(data))


def main():
    senseHat.flip_v()
    senseHat.show_message("Starting...")
    while True:
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
                'tempAvg': temp[3],
                'pressureMb': pressure,
                'humidityPct': humidity
                }
        sendIt(output)
        panelDisplay(output)
        time.sleep(10)


def panelDisplay(data):
    # Work on humidity %
    humidLights = int((data["humidityPct"] / (100/8)))
    pressureLights = int((data["pressureMb"] / (1100/8)))
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
