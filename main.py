import sys
import threading
import time
import random
import sacn
import multiprocessing


def start():
    receiver = sacn.sACNreceiver(bind_address=ipaddress)
    receiver.start()
    receiver.join_multicast(inputUniverse)
    receiver.register_listener('universe', inputData, universe=inputUniverse)
    print("---starting---")


def inputData(packet):
    outputData = list(packet.dmxData)  # eher inputData xD
    dimmerData = [0] * count
    shutterData = [0] * count
    shutterOpen = [True] * count
    global strobeOn, strobeEnginON, valueOld, valueOld2, rndStrobeOn
    dimmer = [0.0] * count

    for x in range(count):
        dimmerData[x] = outputData[fixtureAddress[x] - 1]  # Channel 1
        shutterData[x] = outputData[fixtureAddress[x] + 0]  # Channel 2
        dimmer[x] = dimmerData[x] / 255
        if shutterData[x] <= 10:
            shutterOpen[x] = False
        else:
            shutterOpen[x] = True

        if not shutterOpen[x]:
            dimmer[x] = 0

        if 21 <= shutterData[0] <= 121:
            strobeOn = True

        if 122 <= shutterData[0] <= 222:
            rndStrobeOn = True

        if not (21 <= shutterData[0] <= 121) and strobeOn:
            strobeEnginON = False
            valueOld = 0
            strobeOn = False

        if not (122 <= shutterData[0] <= 222) and rndStrobeOn:
            strobeEnginON = False
            valueOld2 = 0
            rndStrobeOn = False

        if strobeOn:
            value = shutterData[0] - 21
            hz = value * 0.30
            if value != valueOld:
                strobeEnginON = True
                valueOld = value
                conn2.send(hz)

        if rndStrobeOn:
            value2 = shutterData[0] - 122
            hz = value2 * 0.30
            if value2 != valueOld2:
                strobeEnginON = True
                valueOld2 = value2
                conn2.send(hz)

        numberChannels = 4 * 4 * 4
        offset = 9
        for y in range(numberChannels):
            c = (y + offset + fixtureAddress[x] - 1)
            outputData[c] = int(outputData[c] * dimmer[x])

        global dmxPosData
        global dmxColorDataOld
        for i in range(len(dmxPosData)):
            if i in colourAddress:
                dmxPosData[i] = int(outputData[i])
            else:
                dmxColorData[i] = int(outputData[i])
                dmxColorDataOld[i] = int(outputData[i])


def manager(universe, ColourAddressData):
    sender = sacn.sACNsender(source_name='sAcn Backup',
                             fps=50,  # 60  passt net ganz zu den daten von sacn view => 43,48hz
                             bind_address=ipaddress)
    sender.start()
    sender.activate_output(universe)
    sender[universe].multicast = True
    sender[universe].priority = 50

    global dmxPosData, strobeOn
    dmxOut = [0] * 512

    while True:
        for i in range(len(dmxPosData)):
            if i in ColourAddressData:
                dmxOut[i] = int(dmxPosData[i])
            else:
                if strobeOn or rndStrobeOn:
                    dmxOut[i] = int(dmxStrobeData[i])
                else:
                    dmxOut[i] = int(dmxColorData[i])
        sender[universe].dmx_data = dmxOut
        '''
        print("out")
        print(dmxOut)
        print(DmxPosData)
        print(DmxColorData)
        print(DmxStrobeData)
        '''


def strobe(conn, c, addr):
    hz = 1
    numberChannels = 4 * 4 * 4
    offset = 9
    on = False
    global dmxColorData, dmxColorDataOld, dmxStrobeData, strobeEnginON
    while True:
        if conn.poll():
            hz = conn.recv()
            # print(hz)
            on = True
            if hz < 1:  # nicht durch null teilen
                hz = 1
                on = False

        if strobeEnginON:
            rndStrobe = [0] * c
            if rndStrobeOn:
                rnd = [False] * c
                for x in range(c):
                    rnd[x] = random.choice([True, False])
                    if rnd[x]:
                        rndStrobe[x] = 0
                    else:
                        rndStrobe[x] = 1
            else:
                rndStrobe = [1] * c

            for x in range(c):  # all Off
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    dmxStrobeData[var] = int(dmxColorData[var] * 0)
            time.sleep((1 / hz) / 2)
            for x in range(c):  # all ON
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    dmxStrobeData[var] = int(dmxColorDataOld[var] * rndStrobe[x])
            time.sleep((1 / hz) / 2)


if __name__ == '__main__':
    print('argument list', sys.argv)

    ipaddress = sys.argv[1]
    print("IP address: " + ipaddress)

    inputUniverse = 1
    outputUniverse = 2
    fixtureAddress = [1, 75, 149, 223]
    count = 4
    valueOld = 1
    valueOld2 = 1

    dmxPosData = [0] * 512
    dmxColorData = [0] * 512
    dmxColorDataOld = [0] * 512
    dmxStrobeData = [0] * 512

    strobeEnginON = False
    strobeOn = False
    rndStrobeOn = False

    colourAddress = [0, 1, 2, 3, 4, 5, 6, 7, 8, 74, 75, 76, 77, 78, 79, 80,
                     81, 82, 148, 149, 150, 151, 152, 153, 154, 155, 156, 222, 223, 224, 225, 226, 227, 228, 229,
                     230]  # gleich -1 gerechnet python dmx array starting at 0

    #print(colourAddress)

    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    outputManager = threading.Thread(target=manager,
                                     args=(outputUniverse, colourAddress),
                                     name="DataOutputSender")
    inputStrobe = threading.Thread(target=strobe,
                                   args=(conn1, count, fixtureAddress),
                                   name="strobe")
    outputManager.start()
    inputStrobe.start()
    start()
