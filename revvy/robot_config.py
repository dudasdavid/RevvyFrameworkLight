# SPDX-License-Identifier: GPL-3.0-only

import json
import traceback
from json import JSONDecodeError

from revvy.functions import b64_decode_str, dict_get_first
from revvy.scripting.builtin_scripts import builtin_scripts

motor_types = [
    "NotConfigured",
    "RevvyMotor",
    # motor
    [
        [  # left
            "RevvyMotor_CCW",
            "RevvyMotor"
        ],
        [  # right
            "RevvyMotor",
            "RevvyMotor_CCW"
        ]
    ]
]

motor_sides = ["left", "right"]

sensor_types = ["NotConfigured", "HC_SR04", "BumperSwitch"]


class PortConfig:
    def __init__(self):
        self._ports = {}
        self._port_names = {}

    @property
    def names(self):
        return self._port_names

    def __getitem__(self, item):
        return self._ports.get(item, "NotConfigured")

    def __setitem__(self, item, value):
        self._ports[item] = value


class RemoteControlConfig:
    def __init__(self):
        self.analog = []
        self.buttons = [None] * 32


class RobotConfig:
    @staticmethod
    def from_string(config_string):
        try:
            json_config = json.loads(config_string)
        except JSONDecodeError:
            print('Received configuration is not a valid json string')
            print(traceback.format_exc())
            return None

        config = RobotConfig()
        try:
            robot_config = dict_get_first(json_config, ['robotConfig', 'robotconfig'])
            blockly_list = dict_get_first(json_config, ['blocklyList', 'blocklylist'])
        except KeyError:
            print('Received configuration is missing required parts')
            print(traceback.format_exc())
            return None

        try:
            i = 0
            for script in blockly_list:
                try:
                    try:
                        script_name = dict_get_first(script, ['builtinScriptName', 'builtinscriptname'])
                        runnable = builtin_scripts[script_name]
                    except KeyError:
                        source_b64_encoded = dict_get_first(script, ['pythonCode', 'pythoncode'])
                        runnable = b64_decode_str(source_b64_encoded)
                except KeyError:
                    print('Neither builtinScriptName, nor pythonCode is present for a script')
                    raise

                assignments = script['assignments']
                if 'analog' in assignments:
                    for analog_assignment in assignments['analog']:
                        script_name = 'user_script_{}'.format(i)
                        priority = analog_assignment['priority']
                        config.scripts[script_name] = {'script':   runnable,
                                                       'priority': priority}
                        config.controller.analog.append({
                            'channels': analog_assignment['channels'],
                            'script': script_name})
                        i += 1

                if 'buttons' in assignments:
                    for button_assignment in assignments['buttons']:
                        script_name = 'user_script_{}'.format(i)
                        priority = button_assignment['priority']
                        config.scripts[script_name] = {'script': runnable, 'priority': priority}
                        config.controller.buttons[button_assignment['id']] = script_name
                        i += 1

                if 'background' in assignments:
                    script_name = 'user_script_{}'.format(i)
                    priority = assignments['background']
                    config.scripts[script_name] = {'script': runnable, 'priority': priority}
                    config.background_scripts.append(script_name)
                    i += 1
        except (TypeError, IndexError, KeyError, ValueError):
            print('Failed to decode received controller configuration')
            print(traceback.format_exc())
            return None

        try:
            i = 1
            motors = robot_config.get('motors', []) if type(robot_config) is dict else []
            for motor in motors:
                if not motor:
                    motor = {'type': 0}

                if motor['type'] == 0:
                    motor_type = motor_types[motor['type']]

                elif motor['type'] == 1:
                    # motor
                    motor_type = motor_types[1]
                    config.motors.names[motor['name']] = i

                elif motor['type'] == 2:
                    # drivetrain
                    motor_type = motor_types[2][motor['side']][motor['reversed']]
                    config.motors.names[motor['name']] = i
                    config.drivetrain[motor_sides[motor['side']]].append(i)

                else:
                    raise ValueError('Unknown motor type: {}'.format(motor['type']))

                config.motors[i] = motor_type
                i += 1
        except (TypeError, IndexError, KeyError, ValueError):
            print('Failed to decode received motor configuration')
            print(traceback.format_exc())
            return None

        try:
            i = 1
            sensors = robot_config.get('sensors', []) if type(robot_config) is dict else []
            for sensor in sensors:
                if not sensor or sensor['type'] == 0:
                    sensor_type = "NotConfigured"
                else:
                    sensor_type = sensor_types[sensor['type']]
                    config.sensors.names[sensor['name']] = i
                config.sensors[i] = sensor_type

                i += 1

            return config
        except (TypeError, IndexError, KeyError, ValueError):
            print('Failed to decode received sensor configuration')
            print(traceback.format_exc())
            return None

    def __init__(self):
        self.motors = PortConfig()
        self.drivetrain = {'left': [], 'right': []}
        self.sensors = PortConfig()
        self.controller = RemoteControlConfig()
        self.scripts = {}
        self.background_scripts = []


empty_robot_config = RobotConfig()
