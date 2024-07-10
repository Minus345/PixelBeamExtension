import sacn


def start():
    global sender
    global outputUniverse
    inputUniverse = 1
    outputUniverse = 5

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

    count = 1
    # ------ Multitreading loop

    fixtureAddress = 1

    dimmerData = outputData[fixtureAddress - 1]  # Channel 1
    shutterData = outputData[fixtureAddress + 0]  # Channel 2
    dimmer = dimmerData / 255
    if shutterData <= 10:
        shutterOpen = False
    else:
        shutterOpen = True

    if not shutterOpen:
        dimmer = 0

    # -- strobe --

    numberChannels = 4 * 4 * 4
    offset = 9
    for x in range(numberChannels):
        outputData[x + offset] = int(outputData[x + offset] * dimmer)

    sender[outputUniverse].dmx_data = tuple(outputData)
    sender.flush()


if __name__ == '__main__':
    start()
