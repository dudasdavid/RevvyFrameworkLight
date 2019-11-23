# SPDX-License-Identifier: GPL-3.0-only

from revvy.mcu.rrrc_control import RevvyControl


class RobotStatus:
    StartingUp = 0
    NotConfigured = 1
    Configured = 2
    Configuring = 3
    Updating = 4
    Stopped = 5

    _names = {
        StartingUp:    "StartingUp",
        NotConfigured: "NotConfigured",
        Configured:    "Configured",
        Configuring:   "Configuring",
        Updating:      "Updating",
        Stopped:       "Stopped"
    }

    @staticmethod
    def name_of(status):
        return RobotStatus._names.get(status, "Unknown")


class RemoteControllerStatus:
    NotConnected = 0
    ConnectedNoControl = 1
    Controlled = 2

    _names = {
        NotConnected:       "NotConnected",
        ConnectedNoControl: "ConnectedNoControl",
        Controlled:         "Controlled"
    }

    @staticmethod
    def name_of(status):
        return RemoteControllerStatus._names.get(status, "Unknown")


class RobotStatusIndicator:
    master_led_unknown = 0
    master_led_not_configured = 1
    master_led_configured = 2
    master_led_controlled = 3
    master_led_configuring = 4
    master_led_updating = 5

    bluetooth_led_not_connected = 0
    bluetooth_led_connected = 1

    def __init__(self, interface: RevvyControl):
        self._interface = interface

        self._robot_status = RobotStatus.StartingUp
        self._controller_status = RemoteControllerStatus.NotConnected

        self._master_led = self.master_led_not_configured
        self._bluetooth_led = self.bluetooth_led_not_connected

    def _set_master_led(self, value):
        if value != self._master_led:
            self._master_led = value
            self._interface.set_master_status(self._master_led)

    def _set_bluetooth_led(self, value):
        if value != self._bluetooth_led:
            self._bluetooth_led = value
            self._interface.set_bluetooth_connection_status(self._bluetooth_led == self.bluetooth_led_connected)

    def update(self):
        self._interface.set_master_status(self._master_led)
        self._interface.set_bluetooth_connection_status(self._bluetooth_led == self.bluetooth_led_connected)

    def _update_leds(self):
        if self._robot_status == RobotStatus.Configured:
            if self._controller_status == RemoteControllerStatus.Controlled:
                self._set_master_led(self.master_led_controlled)
            else:
                self._set_master_led(self.master_led_configured)

        elif self._robot_status == RobotStatus.Configuring:
            self._set_master_led(self.master_led_configuring)

        elif self._robot_status == RobotStatus.Updating:
            self._set_master_led(self.master_led_updating)

        elif self._robot_status == RobotStatus.NotConfigured:
            self._set_master_led(self.master_led_not_configured)

        elif self._robot_status == RobotStatus.Stopped:
            pass  # don't send status, MCU will reset if it needs to and doesn't if it doesn't (e.g. update)

        else:
            self._set_master_led(self.master_led_unknown)

        if self._controller_status == RemoteControllerStatus.NotConnected:
            self._set_bluetooth_led(self.bluetooth_led_not_connected)
        else:
            self._set_bluetooth_led(self.bluetooth_led_connected)

    @property
    def robot_status(self):
        return self._robot_status

    @robot_status.setter
    def robot_status(self, value):
        print(
            'Robot status change: {} -> {}'.format(RobotStatus.name_of(self._robot_status),
                                                   RobotStatus.name_of(value)))
        if self._robot_status != RobotStatus.Stopped:
            self._robot_status = value
            self._update_leds()

    @property
    def controller_status(self):
        return self._controller_status

    @controller_status.setter
    def controller_status(self, value):
        print('Controller status change: {} -> {}'.format(RemoteControllerStatus.name_of(self._controller_status),
                                                          RemoteControllerStatus.name_of(value)))
        self._controller_status = value
        self._update_leds()
