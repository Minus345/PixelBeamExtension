import sacn


def start():
    global sender
    global outputUniverse
    inputUniverse = 1
    outputUniverse = 2

    receiver = sacn.sACNreceiver(bind_address='192.168.178.131')
    receiver.start()
    receiver.join_multicast(inputUniverse)
    receiver.register_listener('universe', inputData, universe=inputUniverse)

    sender = sacn.sACNsender(source_name='sAcn Backup',
                             fps=40,
                             bind_address='192.168.178.131')
    sender.start()
    sender.activate_output(outputUniverse)
    sender[outputUniverse].multicast = True
    sender[outputUniverse].priority = 50


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

    sender[outputUniverse].dmx_data = tuple(outputData)
    sender.flush()


if __name__ == '__main__':
    start()
