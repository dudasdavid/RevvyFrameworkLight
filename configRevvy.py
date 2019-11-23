from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.rrrc_control import *
import time

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

port_config = Motors["RevvyMotor"]["config"]

(posMin, posMax) = port_config['position_limits']
(posP, posI, posD, speedLowerLimit, speedUpperLimit) = port_config['position_controller']
(speedP, speedI, speedD, powerLowerLimit, powerUpperLimit) = port_config['speed_controller']

config = list(struct.pack("<ll", posMin, posMax))
config += list(struct.pack("<{}".format("f" * 5), posP, posI, posD, speedLowerLimit, speedUpperLimit))
config += list(struct.pack("<{}".format("f" * 5), speedP, speedI, speedD, powerLowerLimit, powerUpperLimit))
config += list(struct.pack("<h", port_config['encoder_resolution']))

print(config)

drivetrainMotors = [1,1,1,2,2,2] # set all to drivetrain LEFT = 1, RIGHT = 2

with RevvyTransportI2C() as transport:
    robot_control = RevvyControl(transport.bind(0x2D))

    print(robot_control.get_firmware_version())
    print(robot_control.get_motor_port_amount())
    print(robot_control.get_sensor_port_amount())

    robot_control.set_master_status(3) # Set master LED green and monitoring communication

    robot_control.set_motor_port_type(1,1) # 0 ='NotConfigured': NullMotor, 1 = 'DcMotor': DcMotorController
    robot_control.set_motor_port_config(1, config)

    robot_control.set_motor_port_type(4, 1)  # 0 ='NotConfigured': NullMotor, 1 = 'DcMotor': DcMotorController
    robot_control.set_motor_port_config(4, config)

    robot_control.set_motor_port_type(5, 1)  # 0 ='NotConfigured': NullMotor, 1 = 'DcMotor': DcMotorController
    robot_control.set_motor_port_config(5, config)

    robot_control.configure_drivetrain(1, drivetrainMotors) # DIFFERENTIAL = 1

    robot_control.set_drivetrain_speed(10,10)

    while True:
        robot_control.ping()
        time.sleep(0.02)
