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
    strobeOn = False
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

        if 21 <= shutterData[0] <= 121 and not strobeOn:
            value = shutterData[0] - 21
            hz = value * 0.35
            conn2.send(hz)
            strobeOn = True

        if not (21 <= shutterData[0] <= 121):
            strobeOn = False
            conn2.send(0)  # sending off ---------- optimal only one time

        numberChannels = 4 * 4 * 4
        offset = 9
        for y in range(numberChannels):
            c = (y + offset + fixtureAddress[x] - 1)
            outputData[c] = int(outputData[c] * dimmer[x])

        global PosData
        for i in range(len(PosData)):  # irgendwie schöner aber geht so auch
            PosData[i] = outputData[i]

        global rgbwBeforeStrobe
        for i in range(len(rgbwBeforeStrobe)):  # irgendwie schöner aber geht so auch
            rgbwBeforeStrobe[i] = outputData[i]


def manager(sharedList, colourData, universe, fixtureAddress):
    sender = sacn.sACNsender(source_name='sAcn Backup',
                             fps=50,  # 60  passt net ganz zu den daten von sacn view => 43,48hz
                             bind_address='192.168.178.131')
    sender.start()
    sender.activate_output(universe)
    # sender.manual_flush = True
    sender[universe].multicast = True
    sender[universe].priority = 50
    dmx = [0] * 512
    offset = 9
    while True:
        # send DMX Data on Change
        # print(sharedList) -------------- sender[universe].dmx_data = sharedList
        for x in range(len(sharedList)):
            startAddr = offset + fixtureAddress[0] - 1
            endFromColorData = fixtureAddress[0] - 1 + offset + 4 * 4 * 4 + 1  # + 1 ?
            #print(startAddr)
            #print(endFromColorData)
            if startAddr < x < endFromColorData:  # edit pos Data
                dmx[x] = int(colourData[x])
            else:
                dmx[x] = int(sharedList[x])
        sender[universe].dmx_data = dmx
        # sender.flush()


def strobe(outputData, colourData, conn, c, addr, beforeStrobe):
    hz = 1
    numberChannels = 4 * 4 * 4
    offset = 9
    on = False
    while True:
        # edit Data to strobe
        if conn.poll():  # if no strobe on -> don't go through the hole loop
            hz = conn.recv()
            # rint(hz)
            on = True
            if hz < 1:  # nicht durch null teilen
                hz = 1
                on = False

        if on:  # if dimmer is off no strobing is necessary
            for x in range(c):  # all Off
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    outputData[var] = int(outputData[var] * 0)
            time.sleep((1 / hz) / 2)
            for x in range(c):  # all ON
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    outputData[var] = int(beforeStrobe[var])  # <------------- hier stehen geblieben
            time.sleep((1 / hz) / 2)


if __name__ == '__main__':
    inputUniverse = 1
    outputUniverse = 2
    fixtureAddress = [1, 75, 149, 223]
    count = 1

    smm = SharedMemoryManager()
    smm.start()
    emptyDmxData = [0] * 512
    emptyDimmerList = [0] * 512
    PosData = smm.ShareableList(emptyDmxData)
    RGBWData = smm.ShareableList(emptyDmxData)
    rgbwBeforeStrobe = smm.ShareableList(emptyDimmerList)

    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    Manager = Process(target=manager, args=(PosData, RGBWData, outputUniverse, fixtureAddress), name="inputManager")
    InputStrobe = Process(target=strobe, args=(PosData, RGBWData, conn1, count, fixtureAddress, rgbwBeforeStrobe),
                          name="strobe")
    Manager.start()
    InputStrobe.start()
    start()
