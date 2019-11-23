# SPDX-License-Identifier: GPL-3.0-only

from revvy.mcu.rrrc_control import RevvyControl


mcu_updater_slots = {
    "motors": {i: i-1 for i in range(1, 7)},
    "sensors": {i: i-1+6 for i in range(1, 5)},
    "battery": 10,
    "axl": 11,
    "gyro": 12,
    "yaw": 13
}


class McuStatusUpdater:
    """Class to read status from the MCU

    This class is the counterpart of McuStatusUpdater/McuStatusUpdaterWrapper implemented on the MCU and is used
    to enable and read specific data slots. It was designed to read multiple pieces of data in one run to decrease
    communication interface overhead, thus to allow lower latency updates"""
    def __init__(self, robot: RevvyControl):
        self._robot = robot
        self._is_enabled = [False] * 32
        self._handlers = [lambda x: None] * 32

    def reset(self):
        print('McuStatusUpdater: reset all slots')
        self._handlers = [lambda x: None] * 32
        self._is_enabled = [False] * 32
        self._robot.status_updater_reset()

    def _enable_slot(self, slot):
        print('McuStatusUpdater: enable slot {}'.format(slot))
        self._robot.status_updater_control(slot, True)

    def _disable_slot(self, slot):
        print('McuStatusUpdater: disable slot {}'.format(slot))
        self._robot.status_updater_control(slot, False)

    def set_slot(self, slot: int, cb):
        assert slot < len(self._handlers)

        if callable(cb):
            if not self._is_enabled[slot]:
                self._is_enabled[slot] = True
                self._handlers[slot] = cb
                self._enable_slot(slot)
        else:
            if self._is_enabled[slot]:
                self._is_enabled[slot] = False
                self._handlers[slot] = lambda x: None
                self._disable_slot(slot)

    def read(self):
        data = self._robot.status_updater_read()

        idx = 0
        while idx < len(data):
            slot = data[idx]
            slot_length = data[idx + 1]

            data_start = idx + 2
            data_end = idx + 2 + slot_length

            if data_end <= len(data):
                self._handlers[slot](data[data_start:data_end])
            else:
                print('McuStatusUpdater: invalid slot length')

            idx = data_end
