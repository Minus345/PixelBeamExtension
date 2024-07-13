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
            print("strobe on...")
            value = shutterData[0] - 21
            hz = value * 0.4
            conn2.send(hz)
            strobeOn = True

        numberChannels = 4 * 4 * 4
        offset = 9
        for y in range(numberChannels):
            c = (y + offset + fixtureAddress[x] - 1)
            outputData[c] = int(outputData[c] * dimmer[x])

        global sl
        for i in range(len(sl)):  # irgendwie schöner aber geht so auch
            sl[i] = outputData[i]

        global dimmerList
        for i in range(len(dimmerList)):  # irgendwie schöner aber geht so auch
            dimmerList[i] = dimmerData[i]


def manager(sharedList, universe):
    sender = sacn.sACNsender(source_name='sAcn Backup',
                             fps=60,  # 60  passt net ganz zu den daten von sacn view => 43,48hz
                             bind_address='192.168.178.131')
    sender.start()
    sender.activate_output(universe)
    # sender.manual_flush = True
    sender[universe].multicast = True
    sender[universe].priority = 50
    dmx = [0] * 512
    while True:
        # send DMX Data on Change
        print(sharedList)  # okay frag einfach nicht -------------- sender[universe].dmx_data = sharedList
        if len(sharedList) > 512 or \
                not all((isinstance(x, int) and (0 <= x <= 255)) for x in sharedList):
            print("-----")
        for x in range(len(sharedList)):
            dmx[x] = int(sharedList[x])
        sender[universe].dmx_data = dmx
        # sender.flush()


def strobe(sharedList, conn, c, addr, dl):
    hz = 1
    numberChannels = 4 * 4 * 4
    offset = 9
    while True:
        # edit Data to strobe
        if conn.poll():  # if no strobe on -> don't go through the hole loop
            hz = conn.recv()
            if hz < 1:  # nicht durch null teilen
                hz = 1

        if sharedList[addr[0] - 1] != 0:  # if dimmer is off no strobing is necessary
            for x in range(c):  # all Off
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    sharedList[var] = int(sharedList[var] * 0)
            time.sleep((1 / hz) / 2)
            for x in range(c):  # all ON
                for y in range(numberChannels):
                    var = (y + offset + addr[x] - 1)
                    sharedList[var] = int(sharedList[var] * dl[x]) # <------------- hier stehen geblieben
            time.sleep((1 / hz) / 2)


if __name__ == '__main__':
    inputUniverse = 1
    outputUniverse = 2
    fixtureAddress = [1, 75, 149, 223]
    count = 4

    smm = SharedMemoryManager()
    smm.start()
    emptyDmxData = [0] * 512
    emptyDimmerList = [0.0] * count
    sl = smm.ShareableList(emptyDmxData)
    dimmerList = smm.ShareableList(emptyDimmerList)

    conn1, conn2 = multiprocessing.Pipe(duplex=True)
    Manager = Process(target=manager, args=(sl, outputUniverse), name="inputManager")
    InputStrobe = Process(target=strobe, args=(sl, conn1, count, fixtureAddress, dimmerList), name="strobe")
    Manager.start()
    InputStrobe.start()
    start()
