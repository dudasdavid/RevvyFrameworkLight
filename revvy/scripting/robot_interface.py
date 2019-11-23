# SPDX-License-Identifier: GPL-3.0-only

import time

from revvy.functions import hex2rgb
from revvy.hardware_dependent.sound import set_volume
from revvy.robot.ports.common import PortInstance, PortCollection


class ResourceWrapper:
    def __init__(self, resource, priority=0):
        self._resource = resource
        self._priority = priority

    def request(self):
        return self._resource.request(self._priority)


class Wrapper:
    def __init__(self, script, resource: ResourceWrapper):
        self._resource = resource
        self._script = script

    @property
    def is_stop_requested(self):
        return self._script.is_stop_requested

    def try_take_resource(self):
        self.check_terminated()
        return self._resource.request()

    def sleep(self, s):
        self._script.sleep(s)

    def check_terminated(self):
        if self.is_stop_requested:
            raise InterruptedError

    def using_resource(self, callback):
        self.if_resource_available(lambda res: res.run_uninterruptable(callback))

    def if_resource_available(self, callback):
        resource = self.try_take_resource()
        if resource:
            try:
                callback(resource)
            finally:
                resource.release()


class SensorPortWrapper(Wrapper):
    """Wrapper class to expose sensor ports to user scripts"""

    def __init__(self, script, sensor: PortInstance, resource):
        super().__init__(script, resource)
        self._sensor = sensor

    def configure(self, config_name):
        self.using_resource(lambda: self._sensor.configure(config_name))

    def read(self):
        """Return the last converted value"""
        start = time.time()
        while not self._sensor.has_data:
            self.check_terminated()
            self.sleep(0.1)
            if time.time() - start > 2:
                raise TimeoutError

        self.check_terminated()
        return self._sensor.value


class RingLedWrapper(Wrapper):
    """Wrapper class to expose LED ring to user scripts"""

    def __init__(self, script, ring_led, resource):
        super().__init__(script, resource)
        self._ring_led = ring_led
        self._user_leds = [0] * ring_led.count

    @property
    def scenario(self):
        return self._ring_led.scenario

    def set_scenario(self, scenario):
        self.using_resource(lambda: self._ring_led.set_scenario(scenario))

    def set(self, led_index, color):
        if type(led_index) is not list:
            led_index = [led_index]

        rgb = hex2rgb(color)

        for idx in led_index:
            if not (1 <= idx <= self._ring_led.count):
                raise IndexError('Led index invalid: {}'.format(idx))
            self._user_leds[idx - 1] = rgb

        self.using_resource(lambda: self._ring_led.display_user_frame(self._user_leds))


class MotorConstants:
    DIRECTION_FWD = 0
    DIRECTION_BACK = 1
    DIRECTION_LEFT = 2
    DIRECTION_RIGHT = 3

    UNIT_ROT = 0
    UNIT_SEC = 1
    UNIT_DEG = 2
    UNIT_TURN_ANGLE = 3

    UNIT_SPEED_RPM = 0
    UNIT_SPEED_PWR = 1

    ACTION_STOP_AND_HOLD = 0
    ACTION_RELEASE = 1


def rpm2dps(rpm):
    """
    >>> rpm2dps(1)
    6
    >>> rpm2dps(60)
    360
    """
    return rpm * 6


class MotorPortWrapper(Wrapper):
    """Wrapper class to expose motor ports to user scripts"""
    max_rpm = 150

    def __init__(self, script, motor: PortInstance, resource):
        super().__init__(script, resource)
        self._motor = motor

    def configure(self, config_name):
        self._motor.configure(config_name)

    def move(self, direction, amount, unit_amount, limit, unit_limit):
        set_fns = {
            MotorConstants.UNIT_DEG: {
                MotorConstants.UNIT_SPEED_RPM: {
                    MotorConstants.DIRECTION_FWD: lambda: self._motor.set_position(amount,
                                                                                   speed_limit=rpm2dps(limit),
                                                                                   pos_type='relative'),
                    MotorConstants.DIRECTION_BACK: lambda: self._motor.set_position(-amount,
                                                                                    speed_limit=rpm2dps(limit),
                                                                                    pos_type='relative'),
                },
                MotorConstants.UNIT_SPEED_PWR: {
                    MotorConstants.DIRECTION_FWD: lambda: self._motor.set_position(amount, power_limit=limit,
                                                                                   pos_type='relative'),
                    MotorConstants.DIRECTION_BACK: lambda: self._motor.set_position(-amount, power_limit=limit,
                                                                                    pos_type='relative')
                }
            },

            MotorConstants.UNIT_ROT: {
                MotorConstants.UNIT_SPEED_RPM: {
                    MotorConstants.DIRECTION_FWD: lambda: self._motor.set_position(360 * amount,
                                                                                   speed_limit=rpm2dps(limit),
                                                                                   pos_type='relative'),
                    MotorConstants.DIRECTION_BACK: lambda: self._motor.set_position(-360 * amount,
                                                                                    speed_limit=rpm2dps(limit),
                                                                                    pos_type='relative'),
                },
                MotorConstants.UNIT_SPEED_PWR: {
                    MotorConstants.DIRECTION_FWD: lambda: self._motor.set_position(360 * amount,
                                                                                   power_limit=limit,
                                                                                   pos_type='relative'),
                    MotorConstants.DIRECTION_BACK: lambda: self._motor.set_position(-360 * amount,
                                                                                    power_limit=limit,
                                                                                    pos_type='relative')
                }
            },

            MotorConstants.UNIT_SEC: {
                MotorConstants.UNIT_SPEED_RPM: {
                    MotorConstants.DIRECTION_FWD: lambda: self._motor.set_speed(rpm2dps(limit)),
                    MotorConstants.DIRECTION_BACK: lambda: self._motor.set_speed(rpm2dps(-limit)),
                },
                MotorConstants.UNIT_SPEED_PWR: {
                    MotorConstants.DIRECTION_FWD: lambda: self._motor.set_speed(rpm2dps(self.max_rpm),
                                                                                power_limit=limit),
                    MotorConstants.DIRECTION_BACK: lambda: self._motor.set_speed(rpm2dps(-self.max_rpm),
                                                                                 power_limit=limit),
                }
            }
        }

        resource = self.try_take_resource()
        if resource:
            try:
                resource.run_uninterruptable(set_fns[unit_amount][unit_limit][direction])

                if unit_amount in [MotorConstants.UNIT_ROT, MotorConstants.UNIT_DEG]:
                    # wait for movement to finish
                    self.sleep(0.2)
                    while not resource.is_interrupted and self._motor.is_moving:
                        self.sleep(0.2)

                elif unit_amount == MotorConstants.UNIT_SEC:
                    self.sleep(amount)
                    resource.run_uninterruptable(lambda: self._motor.set_speed(0))

            finally:
                resource.release()

    def spin(self, direction, rotation, unit_rotation):
        # start moving depending on limits
        set_speed_fns = {
            MotorConstants.UNIT_SPEED_RPM: {
                MotorConstants.DIRECTION_FWD: lambda: self._motor.set_speed(rpm2dps(rotation)),
                MotorConstants.DIRECTION_BACK: lambda: self._motor.set_speed(rpm2dps(-rotation))
            },
            MotorConstants.UNIT_SPEED_PWR: {
                MotorConstants.DIRECTION_FWD: lambda: self._motor.set_speed(rpm2dps(self.max_rpm),
                                                                            power_limit=rotation),
                MotorConstants.DIRECTION_BACK: lambda: self._motor.set_speed(rpm2dps(-self.max_rpm),
                                                                             power_limit=rotation)
            }
        }

        self.using_resource(set_speed_fns[unit_rotation][direction])

    def stop(self, action):
        stop_fn = {
            MotorConstants.ACTION_STOP_AND_HOLD: lambda: self._motor.set_speed(0),
            MotorConstants.ACTION_RELEASE: lambda: self._motor.set_power(0),
        }
        self.using_resource(stop_fn[action])


class DriveTrainWrapper(Wrapper):
    max_rpm = 150

    def __init__(self, script, drivetrain, resource):
        super().__init__(script, resource)
        self._drivetrain = drivetrain

    def drive(self, direction, rotation, unit_rotation, speed, unit_speed):
        multipliers = {
            MotorConstants.DIRECTION_FWD:   1,
            MotorConstants.DIRECTION_BACK: -1,
        }

        set_fns = {
            MotorConstants.UNIT_ROT: {
                MotorConstants.UNIT_SPEED_RPM: lambda: self._drivetrain.move(
                    360 * rotation * multipliers[direction],
                    360 * rotation * multipliers[direction],
                    left_speed=rpm2dps(speed),
                    right_speed=rpm2dps(speed)),

                MotorConstants.UNIT_SPEED_PWR: lambda: self._drivetrain.move(
                    360 * rotation * multipliers[direction],
                    360 * rotation * multipliers[direction],
                    power_limit=speed)
            },
            MotorConstants.UNIT_SEC: {
                MotorConstants.UNIT_SPEED_RPM: lambda: self._drivetrain.set_speeds(
                    rpm2dps(speed) * multipliers[direction],
                    rpm2dps(speed) * multipliers[direction]),

                MotorConstants.UNIT_SPEED_PWR: lambda: self._drivetrain.set_speeds(
                    rpm2dps(self.max_rpm) * multipliers[direction],
                    rpm2dps(self.max_rpm) * multipliers[direction],
                    power_limit=speed)
            }
        }

        resource = self.try_take_resource()
        if resource:
            try:
                resource.run_uninterruptable(set_fns[unit_rotation][unit_speed])

                if unit_rotation == MotorConstants.UNIT_ROT:
                    # wait for movement to finish
                    self.sleep(0.2)
                    while not resource.is_interrupted and self._drivetrain.is_moving:
                        self.sleep(0.2)

                elif unit_rotation == MotorConstants.UNIT_SEC:
                    self.sleep(rotation)

                    resource.run_uninterruptable(lambda: self._drivetrain.set_speeds(0, 0))

            finally:
                resource.release()

    def turn(self, direction, rotation, unit_rotation, speed, unit_speed):
        left_multipliers = {
            MotorConstants.DIRECTION_LEFT: -1,
            MotorConstants.DIRECTION_RIGHT: 1,
        }
        right_multipliers = {
            MotorConstants.DIRECTION_LEFT:  1,
            MotorConstants.DIRECTION_RIGHT: -1,
        }
        turn_multipliers = {
            MotorConstants.DIRECTION_LEFT:  1,  # +ve number -> CCW turn
            MotorConstants.DIRECTION_RIGHT: -1,  # -ve number -> CW turn
        }

        set_fns = {
            MotorConstants.UNIT_SEC: {
                MotorConstants.UNIT_SPEED_RPM: lambda: self._drivetrain.set_speeds(
                    rpm2dps(speed) * left_multipliers[direction],
                    rpm2dps(speed) * right_multipliers[direction]),

                MotorConstants.UNIT_SPEED_PWR: lambda: self._drivetrain.set_speeds(
                    rpm2dps(self.max_rpm) * left_multipliers[direction],
                    rpm2dps(self.max_rpm) * right_multipliers[direction],
                    power_limit=speed)
            },
            MotorConstants.UNIT_TURN_ANGLE: {
                MotorConstants.UNIT_SPEED_RPM: lambda: self._drivetrain.turn(
                    rotation * turn_multipliers[direction],
                    rpm2dps(speed)),

                MotorConstants.UNIT_SPEED_PWR: lambda: self._drivetrain.turn(
                    rotation * turn_multipliers[direction],
                    rpm2dps(self.max_rpm),
                    power_limit=speed)
            }
        }

        resource = self.try_take_resource()
        if resource:
            try:
                resource.run_uninterruptable(set_fns[unit_rotation][unit_speed])

                if unit_rotation == MotorConstants.UNIT_TURN_ANGLE:
                    # wait for movement to finish
                    self.sleep(0.2)
                    while not resource.is_interrupted and self._drivetrain.is_moving:
                        self.sleep(0.2)

                elif unit_rotation == MotorConstants.UNIT_SEC:
                    self.sleep(rotation)

                    resource.run_uninterruptable(lambda: self._drivetrain.set_speeds(0, 0))

            finally:
                resource.release()

    def set_speeds(self, sl, sr):
        resource = self.try_take_resource()
        if resource:
            try:
                self._drivetrain.set_speeds(sl, sr)
            finally:
                if sl == sr == 0:
                    resource.release()


class SoundWrapper(Wrapper):
    def __init__(self, script, sound, resource):
        super().__init__(script, resource)
        self._sound = sound

    def play_tune(self, name):
        self.if_resource_available(lambda resource: self._sound.play_tune(name))


# FIXME: type hints missing because of circular reference that causes ImportError
class RobotInterface:
    """Wrapper class that exposes API to user-written scripts"""

    def __init__(self, script, robot, config, res, priority=0):
        self._start_time = robot.start_time

        resources = {name: ResourceWrapper(res[name], priority) for name in res}

        def motor_name(port):
            return 'motor_{}'.format(port.id)

        def sensor_name(port):
            return 'sensor_{}'.format(port.id)

        motor_wrappers = [MotorPortWrapper(script, port, resources[motor_name(port)]) for port in robot.motors]
        sensor_wrappers = [SensorPortWrapper(script, port, resources[sensor_name(port)]) for port in robot.sensors]
        self._motors = PortCollection(motor_wrappers)
        self._sensors = PortCollection(sensor_wrappers)
        self._motors.aliases.update(config.motors.names)
        self._sensors.aliases.update(config.sensors.names)
        self._sound = SoundWrapper(script, robot.sound, resources['sound'])
        self._ring_led = RingLedWrapper(script, robot.led_ring, resources['led_ring'])
        self._drivetrain = DriveTrainWrapper(script, robot.drivetrain, resources['drivetrain'])

        self._script = script

        # shorthand functions
        self.drive = self._drivetrain.drive
        self.turn = self._drivetrain.turn
        self.play_tune = self._sound.play_tune
        self.set_volume = set_volume

        self.imu = robot.imu

    def stop_all_motors(self, action):
        for motor in self._motors:
            motor.stop(action)

    @property
    def motors(self):
        return self._motors

    @property
    def sensors(self):
        return self._sensors

    @property
    def led(self):
        return self._ring_led

    @property
    def drivetrain(self):
        return self._drivetrain

    def play_note(self): pass  # TODO

    def time(self):
        return time.time() - self._start_time

    # property alias
    led_ring = led
