import serial, time, json

airSerial = serial.Serial('/dev/ttyUSB0')

while True:
    data = []
    for index in range(0,10):
        serIn = airSerial.read()
        data.append(serIn)

    pmTwoFive = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
    pmTen = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10

    output = { 'source': 'particulate', 'pm25': pmTwoFive, 'pm10': pmTen }
    print(json.dumps(output))
    time.sleep(30)




