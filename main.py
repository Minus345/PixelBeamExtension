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
            # conn2.send(hz)
            strobeOn = True

        if not (21 <= shutterData[0] <= 121):
            strobeOn = False
            # conn2.send(0)  # sending off ---------- optimal only one time

        numberChannels = 4 * 4 * 4
        offset = 9
        for y in range(numberChannels):
            c = (y + offset + fixtureAddress[x] - 1)
            outputData[c] = int(outputData[c] * dimmer[x])

        global ColourData
        global PosDataNew
        global rgbwBeforeStrobe
        global ColourAddressData

        for i in range(len(ColourData)):
            ColourData[i] = outputData[i]
            #rgbwBeforeStrobe[i] = outputData[i]

        '''
        for i in range(len(ColourData)):
            if i == 0 or i == 1 or i == 2 or i == 3 or i == 4 or i == 5 or i == 6 or i == 8:
                PosDataNew[i] = int(outputData[i])
            else:
                ColourData[i] = int(outputData[i])
                rgbwBeforeStrobe[i] = int(outputData[i])
                '''

    # print(outputData)
    # print(ColourData)
    # print(PosDataNew)


def manager(colourData, PosData, universe, fixtureAddress, ColourAddressData):
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
        dmx = colourData
        #for x in range(len(colourData)):
        #    dmx[x] = colourData[x]
        sender[universe].dmx_data = dmx
        #print(dmx)

        '''
                for x in range(len(PosData)):
                    startAddr = offset + fixtureAddress[0] - 1
                    endFromColorData = fixtureAddress[0] - 1 + offset + 4 * 4 * 4 + 1  # + 1 ?
                    # print(startAddr)
                    # print(endFromColorData)
                    if x == 0 or x == 1 or x == 2 or x == 3 or x == 4 or x == 5 or x == 6 or x == 8:
                        dmx[x] = int(PosData[x])
                    else:
                        dmx[x] = int(colourData[x])
            '''

        # sender.flush()


def strobe(colourData, outputData, conn, c, addr, beforeStrobe, ColourAddressData):
    hz = 1
    numberChannels = 4 * 4 * 4
    offset = 9
    on = False
    while True:
        # edit Data to strobe
        if conn.poll():  # if no strobe on -> don't go through the hole loop
            # hz = conn.recv()
            # print(hz)
            on = True
            if hz < 1:  # nicht durch null teilen
                hz = 1
                on = False

        if on:
            for x in range(c):  # all Off
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    colourData[var] = int(colourData[var] * 0)
            time.sleep((1 / hz) / 2)
            for x in range(c):  # all ON
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    colourData[var] = int(beforeStrobe[var])  # <------------- hier stehen geblieben
            time.sleep((1 / hz) / 2)


if __name__ == '__main__':
    inputUniverse = 1
    outputUniverse = 2
    fixtureAddress = [1, 75, 149, 223]
    count = 1

    ColourAddressData = [0, 1, 2, 3, 4, 5, 6, 8]  # gleich -1 gerechnet python dmx array starting at 0

    smm = SharedMemoryManager()
    smm.start()
    ColourData = smm.ShareableList([0] * 512)
    #PosDataNew = smm.ShareableList([0] * 512)
    #rgbwBeforeStrobe = smm.ShareableList([0] * 512)

    PosDataNew = None
    rgbwBeforeStrobe = None

    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    Manager = Process(target=manager, args=(ColourData, PosDataNew, outputUniverse, fixtureAddress, ColourAddressData),
                      name="DataOutputSender")
    InputStrobe = Process(target=strobe, args=(
        ColourData, PosDataNew, conn1, count, fixtureAddress, rgbwBeforeStrobe, ColourAddressData),
                          name="strobe")
    Manager.start()
    InputStrobe.start()
    start()
