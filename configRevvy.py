from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.commands import *
from revvy.robot.ports.motor import create_motor_port_handler

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

        self.status_updater_reset = McuStatusUpdater_ResetCommand(transport)
        self.status_updater_control = McuStatusUpdater_ControlCommand(transport)
        self.status_updater_read = McuStatusUpdater_ReadCommand(transport)

Motors = {
    'NotConfigured': {'driver': 'NotConfigured', 'config': {}},
    'RevvyMotor':    {
        'driver': 'DcMotor',
        'config': {
            'speed_controller':    [1 / 37.5, 0.3, 0, -100, 100],
            'position_controller': [10, 0, 0, -900, 900],
            'position_limits':     [0, 0],
            'encoder_resolution':  1536
        }
    },
    'RevvyMotor_CCW': {
        'driver': 'DcMotor',
        'config': {
            'speed_controller':    [1 / 37.5, 0.3, 0, -100, 100],
            'position_controller': [10, 0, 0, -900, 900],
            'position_limits':     [0, 0],
            'encoder_resolution': -1536
        }
    }
}

Sensors = {
    'NotConfigured': {'driver': 'NotConfigured', 'config': {}},
    'HC_SR04':       {'driver': 'HC_SR04', 'config': {}},
    'BumperSwitch':  {'driver': 'BumperSwitch', 'config': {}},
}



with RevvyTransportI2C() as transport:
    robot_control = RevvyControl(transport.bind(0x2D))

    print(robot_control.get_firmware_version())
    print(robot_control.get_motor_port_amount())
    print(robot_control.get_sensor_port_amount())

    motorPorts = create_motor_port_handler(robot_control, Motors)

    #robot_control.set_motor_port_config(4, config)
    #robot_control.status_updater_control(4)
