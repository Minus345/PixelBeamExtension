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
    outputData = list(packet.dmxData)

    count = 4
    fixtureAddress = [1, 75, 149, 223]
    dimmerData = [0] * count
    shutterData = [0] * count
    shutterOpen = [True] * count
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

        # -- strobe --

        numberChannels = 4 * 4 * 4
        offset = 9
        for y in range(numberChannels):
            c = (y + offset + fixtureAddress[x] - 1)
            outputData[c] = int(outputData[c] * dimmer[x])

    global sl

    for i in range(len(sl)):  # irgendwie schöner aber geht so auch
        sl[i] = outputData[i]


def manager(sharedList, universe):
    sender = sacn.sACNsender(source_name='sAcn Backup',
                             fps=60,  # passt net ganz zu den daten von sacn view => 43,48hz
                             bind_address='192.168.178.131')
    sender.start()
    sender.activate_output(universe)
    sender[universe].multicast = True
    sender[universe].priority = 50
    while True:
        # send DMX Data on Change
        # print(sharedList)
        sender[universe].dmx_data = sharedList


def strobe(sharedList):
    while True:
        # edit Data to strobe
        print("strobe")
        time.sleep(1)


if __name__ == '__main__':
    inputUniverse = 1
    outputUniverse = 2

    smm = SharedMemoryManager()
    smm.start()
    emptyDmxData = [0] * 512
    sl = smm.ShareableList(emptyDmxData)

    Manager = Process(target=manager, args=(sl, outputUniverse))
    InputStrobe = Process(target=strobe, args=(sl,))
    Manager.start()
    start()
