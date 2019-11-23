# SPDX-License-Identifier: GPL-3.0-only


class Sound:
    def __init__(self, setup, play, sounds=None):
        if sounds is None:
            sounds = {}
        setup()

        self._play = play
        self._sounds = sounds

    def play_tune(self, name):
        try:
            self._play(self._sounds[name])
        except KeyError:
            print('Sound not found: {}'.format(name))
