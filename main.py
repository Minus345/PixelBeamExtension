import threading
import time
from multiprocessing import Process

import sacn
import multiprocessing
from multiprocessing.managers import SharedMemoryManager


def start():
    receiver = sacn.sACNreceiver(bind_address='192.168.178.131')
    receiver.start()
    receiver.join_multicast(inputUniverse)
    receiver.register_listener('universe', inputData, universe=inputUniverse)
    print("---starting---")


def inputData(packet):
    outputData = list(packet.dmxData)  # eher inputData xD
    dimmerData = [0] * count
    shutterData = [0] * count
    shutterOpen = [True] * count
    global strobeOn
    dimmer = [0.0] * count
    hz = 0

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

        if not (21 <= shutterData[0] <= 121):
            strobeOn = False
            # conn2.send(0)  # sending off ---------- optimal only one time

        if strobeOn:
            global valueOld
            value = shutterData[0] - 21
            hz = value * 0.35
            if value != valueOld:
                valueOld = value
                conn2.send(hz)

        numberChannels = 4 * 4 * 4
        offset = 9
        for y in range(numberChannels):
            c = (y + offset + fixtureAddress[x] - 1)
            outputData[c] = int(outputData[c] * dimmer[x])

        global DmxPosData
        global DMXOld
        for i in range(len(DmxPosData)):
            if i == 0 or i == 1 or i == 2 or i == 3 or i == 4 or i == 5 or i == 6 or i == 8:
                DmxPosData[i] = int(outputData[i])
            else:
                DmxColorData[i] = int(outputData[i])
                DMXOld[i] = int(outputData[i])


def manager(universe, fixtureAddress, ColourAddressData):
    sender = sacn.sACNsender(source_name='sAcn Backup',
                             fps=50,  # 60  passt net ganz zu den daten von sacn view => 43,48hz
                             bind_address='192.168.178.131')
    sender.start()
    sender.activate_output(universe)
    sender[universe].multicast = True
    sender[universe].priority = 50

    global DmxPosData
    global strobeOn
    dmxOut = [0] * 512

    while True:
        for i in range(len(DmxPosData)):
            if i == 0 or i == 1 or i == 2 or i == 3 or i == 4 or i == 5 or i == 6 or i == 8:
                dmxOut[i] = int(DmxPosData[i])
            else:
                if strobeOn:
                    dmxOut[i] = int(DmxStrobeData[i])
                else:
                    dmxOut[i] = int(DmxColorData[i])
        sender[universe].dmx_data = dmxOut
        '''
        print("out")
        print(dmxOut)
        print(DmxPosData)
        print(DmxColorData)
        print(DmxStrobeData)
        '''


def strobe(conn, c, addr, ColourAddressData):
    hz = 1
    numberChannels = 4 * 4 * 4
    offset = 9
    on = False
    global DmxColorData
    global DMXOld
    global DmxStrobeData
    while True:
        # edit Data to strobe
        if conn.poll():  # if no strobe on -> don't go through the hole loop
            hz = conn.recv()
            print(hz)
            on = True
            if hz < 1:  # nicht durch null teilen
                hz = 1
                on = False

        if on:
            for x in range(c):  # all Off
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    DmxStrobeData[var] = int(DmxColorData[var] * 0)
            time.sleep((1 / hz) / 2)
            for x in range(c):  # all ON
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    DmxStrobeData[var] = DMXOld[var]  # <------------- hier stehen geblieben
            time.sleep((1 / hz) / 2)


if __name__ == '__main__':
    inputUniverse = 1
    outputUniverse = 2
    fixtureAddress = [1, 75, 149, 223]
    count = 1
    valueOld = 1

    DmxPosData = [0] * 512
    DmxColorData = [0] * 512
    DMXOld = [0] * 512
    DmxStrobeData = [0] * 512

    strobeOn = False

    ColourAddressData = [0, 1, 2, 3, 4, 5, 6, 8]  # gleich -1 gerechnet python dmx array starting at 0

    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    Manager = threading.Thread(target=manager,
                               args=(outputUniverse, fixtureAddress, ColourAddressData),
                               name="DataOutputSender")
    InputStrobe = threading.Thread(target=strobe,
                                   args=(conn1, count, fixtureAddress, ColourAddressData),
                                   name="strobe")
    Manager.start()
    InputStrobe.start()
    start()
