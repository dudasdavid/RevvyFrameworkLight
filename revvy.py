#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-only

from revvy.bluetooth.ble_revvy import Observable, RevvyBLE
from revvy.file_storage import FileStorage, MemoryStorage
from revvy.functions import getserial, read_json
from revvy.bluetooth.longmessage import LongMessageHandler, LongMessageStorage, LongMessageType, LongMessageStatus
from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.robot_config import empty_robot_config
from revvy.utils import *
from revvy.mcu.rrrc_transport import *
from revvy.mcu.rrrc_control import *
import sys

default_robot_config = None

class LongMessageImplementation:
    # TODO: this, together with the other long message classes is probably a lasagna worth simplifying
    def __init__(self, robot: RobotManager, ignore_config):
        self._robot = robot
        self._ignore_config = ignore_config

    def on_upload_started(self, message_type):
        """Visual indication that an upload has started

        Requests LED ring change in the background"""

        if message_type == LongMessageType.FRAMEWORK_DATA:
            self._robot.run_in_background(lambda: self._robot.robot.led_ring.set_scenario(RingLed.ColorWheel))
        else:
            self._robot.robot.status.robot_status = RobotStatus.Configuring

    def on_transmission_finished(self, message_type):
        """Visual indication that an upload has finished

        Requests LED ring change in the background"""

        if message_type != LongMessageType.FRAMEWORK_DATA:
            self._robot.run_in_background(lambda: self._robot.robot.led_ring.set_scenario(RingLed.BreathingGreen))

    def on_message_updated(self, storage, message_type):
        print('Received message: {}'.format(message_type))

        if message_type == LongMessageType.TEST_KIT:
            message_data = storage.get_long_message(message_type).decode()
            print('Running test script: {}'.format(message_data))

            robot = self._robot

            def start_script():
                print("Starting new test script")
                robot._scripts.add_script("test_kit", message_data, 0)
                robot._scripts["test_kit"].on_stopped(lambda: robot.configure(None))

                # start can't run in on_stopped handler because overwriting script causes deadlock
                robot.run_in_background(lambda: robot._scripts["test_kit"].start())

            self._robot.configure(empty_robot_config, start_script)

        elif message_type == LongMessageType.CONFIGURATION_DATA:
            message_data = storage.get_long_message(message_type).decode()
            print('New configuration: {}'.format(message_data))
            if self._ignore_config:
                print('New configuration ignored')
            else:
                parsed_config = RobotConfig.from_string(message_data)
                if parsed_config is not None:
                    self._robot.configure(parsed_config, self._robot.start_remote_controller)

        elif message_type == LongMessageType.FRAMEWORK_DATA:
            self._robot.robot.status.robot_status = RobotStatus.Updating
            self._robot.request_update()

def start_revvy(config: RobotConfig = None):
    current_installation = os.path.dirname(os.path.realpath(__file__))
    os.chdir(current_installation)

    # base directories
    package_data_dir = os.path.join(current_installation, 'data')


    print('Revvy run from {} ({})'.format(current_installation, __file__))

    # prepare environment

    serial = getserial()

    manifest = read_json('manifest.json')

    sound_files = {
        'alarm_clock':    'alarm_clock.mp3',
        'bell':           'bell.mp3',
        'buzzer':         'buzzer.mp3',
        'car_horn':       'car-horn.mp3',
        'cat':            'cat.mp3',
        'dog':            'dog.mp3',
        'duck':           'duck.mp3',
        'engine_revving': 'engine-revving.mp3',
        'lion':           'lion.mp3',
        'oh_no':          'oh-no.mp3',
        'robot':          'robot.mp3',
        'robot2':         'robot2.mp3',
        'siren':          'siren.mp3',
        'ta_da':          'tada.mp3',
        'uh_oh':          'uh-oh.mp3',
        'yee_haw':        'yee-haw.mp3',
    }

    def sound_path(file):
        return os.path.join(package_data_dir, 'assets', file)

    sound_paths = {key: sound_path(sound_files[key]) for key in sound_files}

    device_name = Observable("ROS")

    ble_storage_dir = os.path.join(current_installation, 'ble')
    ble_storage = FileStorage(ble_storage_dir)
    long_message_storage = LongMessageStorage(ble_storage, MemoryStorage())
    long_message_handler = LongMessageHandler(long_message_storage)

    ble = RevvyBLE(device_name, serial, long_message_handler)

    # if the robot has never been configured, set the default configuration for the simple robot
    initial_config = default_robot_config

    with RevvyTransportI2C() as transport:
        robot_control = RevvyControl(transport.bind(0x2D))

        robot = RobotManager(robot_control, ble, sound_paths, manifest['version'], initial_config)

        lmi = LongMessageImplementation(robot, config is not None)
        long_message_handler.on_upload_started(lmi.on_upload_started)
        long_message_handler.on_upload_finished(lmi.on_transmission_finished)
        long_message_handler.on_message_updated(lmi.on_message_updated)

        # noinspection PyBroadException
        try:
            robot.start()

            print("Press Enter to exit")
            input()
            # manual exit
            ret_val = RevvyStatusCode.OK
        except EOFError:
            robot.needs_interrupting = False
            while not robot.exited:
                time.sleep(1)
            ret_val = robot.status_code
        except KeyboardInterrupt:
            # manual exit or update request
            ret_val = robot.status_code
        except Exception:
            print(traceback.format_exc())
            ret_val = RevvyStatusCode.ERROR
        finally:
            print('stopping')
            robot.stop()

        print('terminated.')
        return ret_val


if __name__ == "__main__":
    sys.exit(start_revvy())
