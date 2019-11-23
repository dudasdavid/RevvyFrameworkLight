from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.commands import *

class RevvyControl:
    def __init__(self, transport: RevvyTransport):
        self.ping = PingCommand(transport)
        self.get_firmware_version = ReadFirmwareVersionCommand(transport)

with RevvyTransportI2C() as transport:
    robot_control = RevvyControl(transport.bind(0x2D))

    print(robot_control.get_firmware_version())