# SPDX-License-Identifier: GPL-3.0-only

import subprocess
import threading

from revvy.functions import map_values, clip

max_parallel_sounds = 4
default_volume = 90

init_amp = [
    [  # v1
        'gpio -g mode 13 alt0',
        'gpio -g mode 22 out'
    ],
    [  # v2
        'gpio -g mode 13 alt0',
        'gpio -g mode 22 out',
        'gpio write 3 1'
    ]
]
enable_amp = [
    "gpio write 3 1",  # v1
    "gpio write 3 0",  # v2
]
disable_amp = [
    "gpio write 3 0",  # v1
    "gpio write 3 1",  # v2
]
current_hw = 0
lock = threading.Lock()
processes = []


def _run_command(commands):
    if type(commands) is str:
        commands = [commands]

    command = '; '.join(commands)
    return subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)


def _run_command_with_callback(commands, callback):
    def run_in_thread(args):
        process = _run_command(args)
        with lock:
            processes.append(process)

        process.wait()

        with lock:
            processes.remove(process)

        callback()

    thread = threading.Thread(target=run_in_thread, args=(commands,))
    thread.start()


def _disable_amp_callback():
    print('Disable amp callback')
    with lock:
        print("Sounds playing: {}".format(len(processes)))
        if not processes:
            print('Turning amp off')
            _run_command(disable_amp[current_hw])


def _init_sound(hw):
    global current_hw
    current_hw = hw
    _run_command(init_amp[hw]).wait()


def _play_sound(hw, sound):
    if len(processes) <= max_parallel_sounds:
        print('Playing sound: {}'.format(sound))

        _run_command_with_callback([
            enable_amp[hw],
            "mpg123 {}".format(sound)
        ], _disable_amp_callback)
    else:
        print('Too many sounds are playing, skip')


def setup_sound_v1():
    _init_sound(0)


def setup_sound_v2():
    _init_sound(1)


def play_sound_v1(sound):
    _play_sound(0, sound)


def play_sound_v2(sound):
    _play_sound(1, sound)


def set_volume(volume):
    scaled = map_values(clip(volume, 0, 100), 0, 100, -10239, 400)
    _run_command('amixer cset numid=1 -- {}'.format(scaled))


def reset_volume():
    set_volume(default_volume)
