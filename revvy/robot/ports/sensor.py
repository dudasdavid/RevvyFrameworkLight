# SPDX-License-Identifier: GPL-3.0-only

from collections import namedtuple

from revvy.mcu.rrrc_control import RevvyControl
from revvy.robot.ports.common import PortHandler, PortInstance


SensorValue = namedtuple('SensorValue', ['raw', 'converted'])


def create_sensor_port_handler(interface: RevvyControl, configs: dict):
    port_amount = interface.get_sensor_port_amount()
    port_types = interface.get_sensor_port_types()

    drivers = {
        'NotConfigured': NullSensor,
        'BumperSwitch': bumper_switch,
        'HC_SR04': hcsr04
    }
    handler = PortHandler(interface, configs, drivers, port_amount, port_types)
    handler._set_port_type = interface.set_sensor_port_type

    return handler


class NullSensor:
    def __init__(self, port: PortInstance, port_config):
        pass

    def on_value_changed(self, cb):
        pass

    def update_status(self, data):
        pass

    def read(self):
        return SensorValue(raw=0, converted=0)

    @property
    def value(self):
        return 0

    @property
    def raw_value(self):
        return 0


class BaseSensorPortDriver:
    def __init__(self, port: PortInstance):
        self._port = port
        self._interface = port.interface
        self._value = None
        self._raw_value = None
        self._value_changed_callback = lambda p: None

    @property
    def has_data(self):
        return self._value is not None

    def update_status(self, data):
        if len(data) == 0:
            self._value = None
            return

        old_raw = self._raw_value
        if old_raw != data:
            converted = self.convert_sensor_value(data)

            self._raw_value = data
            if converted is not None:
                self._value = converted

            self._raise_value_changed_callback()

    def read(self):
        data = self._interface.get_sensor_port_value(self._port.id)
        self.update_status(data)

        return SensorValue(raw=self._raw_value, converted=self._value)

    @property
    def value(self):
        return self._value

    @property
    def raw_value(self):
        return self._raw_value

    def on_value_changed(self, cb):
        if not callable(cb):

            def empty_fn(p):
                pass

            cb = empty_fn

        self._value_changed_callback = cb

    def _raise_value_changed_callback(self):
        self._value_changed_callback(self._port)

    def convert_sensor_value(self, raw): raise NotImplementedError


# noinspection PyUnusedLocal
def bumper_switch(port: PortInstance, cfg):
    sensor = BaseSensorPortDriver(port)

    def process_bumper(raw):
        assert len(raw) == 2
        return raw[0] == 1

    sensor.convert_sensor_value = process_bumper
    return sensor


# noinspection PyUnusedLocal
def hcsr04(port: PortInstance, cfg):
    sensor = BaseSensorPortDriver(port)

    def process_ultrasonic(raw):
        assert len(raw) == 4
        dst = int.from_bytes(raw, byteorder='little')
        if dst == 0:
            return None
        return dst

    sensor.convert_sensor_value = process_ultrasonic
    return sensor
