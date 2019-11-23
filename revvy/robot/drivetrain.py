# SPDX-License-Identifier: GPL-3.0-only

from revvy.mcu.rrrc_control import RevvyControl


class DrivetrainTypes:
    NONE = 0
    DIFFERENTIAL = 1


class DifferentialDrivetrain:
    NOT_ASSIGNED = 0
    LEFT = 1
    RIGHT = 2

    CONTROL_GO_POS = 0
    CONTROL_GO_SPD = 1
    CONTROL_STOP = 2

    def __init__(self, interface: RevvyControl, motor_port_count):
        self._interface = interface
        self._motor_count = motor_port_count
        self._motors = []
        self._left_motors = []
        self._right_motors = []

        self.set_speeds = interface.set_drivetrain_speed
        self.turn = interface.drivetrain_turn
        self.move = interface.set_drivetrain_position

    @property
    def motors(self):
        return self._motors

    def reset(self):
        self._motors.clear()
        self._left_motors.clear()
        self._right_motors.clear()

        self.configure()

    def add_left_motor(self, motor):
        print('Drivetrain: Add motor {} to left side'.format(motor.id))
        self._motors.append(motor)
        self._left_motors.append(motor.id - 1)

    def add_right_motor(self, motor):
        print('Drivetrain: Add motor {} to right side'.format(motor.id))
        self._motors.append(motor)
        self._right_motors.append(motor.id - 1)

    def configure(self):
        motors = [DifferentialDrivetrain.NOT_ASSIGNED] * self._motor_count
        for motor in self._left_motors:
            motors[motor] = DifferentialDrivetrain.LEFT
        for motor in self._right_motors:
            motors[motor] = DifferentialDrivetrain.RIGHT

        self._interface.configure_drivetrain(DrivetrainTypes.DIFFERENTIAL, motors)

    @property
    def is_moving(self):
        return any(motor.is_moving for motor in self._motors)
