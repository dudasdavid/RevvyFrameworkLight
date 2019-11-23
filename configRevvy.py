from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.commands import *

class RevvyControl:
    def __init__(self, transport: RevvyTransport):
        self.ping = PingCommand(transport)

        self.get_hardware_version = ReadHardwareVersionCommand(transport)
        self.get_firmware_version = ReadFirmwareVersionCommand(transport)

        self.get_motor_port_amount = ReadMotorPortAmountCommand(transport)
        self.get_motor_port_types = ReadMotorPortTypesCommand(transport)
        self.set_motor_port_type = SetMotorPortTypeCommand(transport)
        self.set_motor_port_config = SetMotorPortConfigCommand(transport)
        self.set_motor_port_control_value = SetMotorPortControlCommand(transport)
        self.get_motor_position = ReadMotorPortStatusCommand(transport)

        self.configure_drivetrain = ConfigureDrivetrain(transport)
        self.set_drivetrain_position = RequestDifferentialDriveTrainPositionCommand(transport)
        self.set_drivetrain_speed = RequestDifferentialDriveTrainSpeedCommand(transport)
        self.drivetrain_turn = RequestDifferentialDriveTrainTurnCommand(transport)

        self.get_sensor_port_amount = ReadSensorPortAmountCommand(transport)
        self.get_sensor_port_types = ReadSensorPortTypesCommand(transport)
        self.set_sensor_port_type = SetSensorPortTypeCommand(transport)
        self.set_sensor_port_config = SetSensorPortConfigCommand(transport)
        self.get_sensor_port_value = ReadSensorPortStatusCommand(transport)

with RevvyTransportI2C() as transport:
    robot_control = RevvyControl(transport.bind(0x2D))

    print(robot_control.get_firmware_version())
    print(robot_control.get_motor_port_amount())
    print(robot_control.get_sensor_port_amount())