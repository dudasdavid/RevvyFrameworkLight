# SPDX-License-Identifier: GPL-3.0-only

import math


def stick_controller(x, y):
    """Two wheel speeds are controlled independently, just pass through

    >>> stick_controller(0, 0)
    (0, 0)
    >>> stick_controller(0.2, 0.3)
    (0.2, 0.3)
    >>> stick_controller(-0.2, -0.3)
    (-0.2, -0.3)
    """
    return x, y


def generic_joystick(x, y, factor):
    """Calculate control vector length and angle based on touch (x, y) coordinates with configurable exponential rate"""

    if x == y == 0:
        return 0.0, 0.0

    angle = math.atan2(y, x) - math.pi / 2
    length = math.sqrt(x * x + y * y)

    length = (1 - factor) * (length ** 3) + (factor * length)

    v = length * math.cos(angle)
    w = length * math.sin(angle)

    sr = round(v + w, 3)
    sl = round(v - w, 3)
    return sl, sr


def joystick(x, y):
    """Calculate control vector length and angle based on touch (x, y) coordinates

    >>> joystick(0, 0)
    (0.0, 0.0)
    >>> joystick(0, 1)
    (1.0, 1.0)
    >>> joystick(0, -1)
    (-1.0, -1.0)
    >>> joystick(1, 0)
    (1.0, -1.0)
    >>> joystick(-1, 0)
    (-1.0, 1.0)
    """

    return generic_joystick(x, y, 1)


def expo_joystick(x, y):
    """Calculate control vector length and angle based on touch (x, y) coordinates, using exponential rate

    >>> expo_joystick(0, 0)
    (0.0, 0.0)
    >>> expo_joystick(0, 1)
    (1.0, 1.0)
    >>> expo_joystick(0, -1)
    (-1.0, -1.0)
    >>> expo_joystick(1, 0)
    (1.0, -1.0)
    >>> expo_joystick(-1, 0)
    (-1.0, 1.0)
    >>> expo_joystick(0.5, 0)
    (0.312, -0.312)
    """

    return generic_joystick(x, y, 0.5)
