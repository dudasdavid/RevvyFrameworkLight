# SPDX-License-Identifier: GPL-3.0-only


def empty_callback():
    pass


class EdgeTrigger:
    def __init__(self):
        self._rising_edge = empty_callback
        self._falling_edge = empty_callback
        self._previous = 0

    def on_rising_edge(self, l):
        self._rising_edge = l

    def on_falling_edge(self, l):
        self._falling_edge = l

    def handle(self, value):
        if value > self._previous:
            self._rising_edge()
        elif value < self._previous:
            self._falling_edge()
        self._previous = value


class LevelTrigger:
    def __init__(self):
        self._high = empty_callback
        self._low = empty_callback

    def on_high(self, l):
        self._high = l

    def on_low(self, l):
        self._low = l

    def handle(self, value):
        if value > 0:
            self._high()
        else:
            self._low()


class ToggleButton:
    def __init__(self):
        self._on_enabled = empty_callback
        self._on_disabled = empty_callback
        self._edge_detector = EdgeTrigger()
        self._edge_detector.on_rising_edge(self._toggle)
        self._is_enabled = False

    def _toggle(self):
        self._is_enabled = not self._is_enabled
        if self._is_enabled:
            self._on_enabled()
        else:
            self._on_disabled()

    def on_enabled(self, l):
        self._on_enabled = l

    def on_disabled(self, l):
        self._on_disabled = l

    def handle(self, value):
        self._edge_detector.handle(0 if value <= 0 else 1)
