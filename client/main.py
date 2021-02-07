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
        time.sleep(10)


main()
