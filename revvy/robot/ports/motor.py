# SPDX-License-Identifier: GPL-3.0-only

from collections import namedtuple

import math

from revvy.mcu.rrrc_control import RevvyControl
from revvy.robot.ports.common import PortHandler, PortInstance
import struct


DcMotorStatus = namedtuple("DcMotorStatus", ['position', 'speed', 'power'])


def create_motor_port_handler(interface: RevvyControl, configs: dict):
    port_amount = interface.get_motor_port_amount()
    port_types = interface.get_motor_port_types()

    drivers = {
        'NotConfigured': NullMotor,
        'DcMotor': DcMotorController
    }
    handler = PortHandler(interface, configs, drivers, port_amount, port_types)
    handler._set_port_type = interface.set_motor_port_type

    return handler


class NullMotor:
    def __init__(self, port: PortInstance, port_config):
        pass

    def on_status_changed(self, cb):
        pass

    @property
    def speed(self):
        return 0

    @property
    def position(self):
        return 0

    @property
    def power(self):
        return 0

    @property
    def is_moving(self):
        return False

    def set_speed(self, speed, power_limit=None):
        pass

    def set_position(self, position: int, speed_limit=None, power_limit=None, pos_type='absolute'):
        pass

    def set_power(self, power):
        pass

    def update_status(self, data):
        pass

    def get_status(self):
        return DcMotorStatus(position=0, speed=0, power=0)


class DcMotorController:
    """Generic driver for dc motors"""
    def __init__(self, port: PortInstance, port_config):
        self._name = 'Motor {}'.format(port.id)
        self._port = port

        self._configure = lambda cfg: port.interface.set_motor_port_config(port.id, cfg)
        self._read = lambda: port.interface.get_motor_position(port.id)

        self._pos = 0
        self._speed = 0
        self._power = 0
        self._pos_reached = None

        (posMin, posMax) = port_config['position_limits']
        (posP, posI, posD, speedLowerLimit, speedUpperLimit) = port_config['position_controller']
        (speedP, speedI, speedD, powerLowerLimit, powerUpperLimit) = port_config['speed_controller']

        config = list(struct.pack("<ll", posMin, posMax))
        config += list(struct.pack("<{}".format("f" * 5), posP, posI, posD, speedLowerLimit, speedUpperLimit))
        config += list(struct.pack("<{}".format("f" * 5), speedP, speedI, speedD, powerLowerLimit, powerUpperLimit))
        config += list(struct.pack("<h", port_config['encoder_resolution']))

        print('{}: Sending configuration: {}'.format(self._name, config))

        self._configure(config)
        self._status_changed_callback = lambda p: None

    def _control(self, ctrl, value, pos_ctrl=False):
        self._pos_reached = False if pos_ctrl else None
        self._port.interface.set_motor_port_control_value(self._port.id, [ctrl] + value)

    def on_status_changed(self, cb):
        if not callable(cb):

            def empty_fn(p):
                pass

            cb = empty_fn

        self._status_changed_callback = cb

    def _raise_status_changed_callback(self):
        self._status_changed_callback(self._port)

    @property
    def speed(self):
        return self._speed

    @property
    def position(self):
        return self._pos

    @property
    def power(self):
        return self._power

    @property
    def is_moving(self):
        stopped = math.fabs(round(self._speed, 2)) == 0 and math.fabs(self._power) < 80
        if self._pos_reached is None:
            return not stopped
        else:
            return not (self._pos_reached and stopped)

    def set_speed(self, speed, power_limit=None):
        print('{}::set_speed'.format(self._name))
        control = list(struct.pack("<f", speed))
        if power_limit is not None:
            control += list(struct.pack("<f", power_limit))

        self._control(1, control)

    def set_position(self, position: int, speed_limit=None, power_limit=None, pos_type='absolute'):
        print('{}::set_position'.format(self._name))
        control = list(struct.pack('<l', position))

        if speed_limit is not None and power_limit is not None:
            control += list(struct.pack("<ff", speed_limit, power_limit))
        elif speed_limit is not None:
            control += list(struct.pack("<bf", 1, speed_limit))
        elif power_limit is not None:
            control += list(struct.pack("<bf", 0, power_limit))

        pos_request_types = {'absolute': 2, 'relative': 3}
        self._control(pos_request_types[pos_type], control, True)

    def set_power(self, power):
        print('{}::set_power'.format(self._name))
        self._control(0, [power])

    def update_status(self, data):
        if len(data) == 9:
            (pos, speed, power) = struct.unpack('<lfb', bytearray(data))
            pos_reached = None
        elif len(data) == 10:
            (pos, speed, power, pos_reached) = struct.unpack('<lfbb', bytearray(data))
        else:
            print('{}: Received {} bytes of data instead of 9 or 10'.format(self._name, len(data)))
            return

        self._pos = pos
        self._speed = speed
        self._power = power
        self._pos_reached = pos_reached

        self._raise_status_changed_callback()

    def get_status(self):
        data = self._read()

        self.update_status(data)
        return DcMotorStatus(position=self._pos, speed=self._speed, power=self._power)
