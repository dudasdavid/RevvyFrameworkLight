# SPDX-License-Identifier: GPL-3.0-only

from threading import Lock


class ResourceHandle:
    def __init__(self, resource, callback=lambda: None):
        self._resource = resource
        self._callback = callback
        self._is_interrupted = False

    def release(self):
        self._resource.release(self)

    def interrupt(self):
        self._is_interrupted = True
        self._callback()

    def run_uninterruptable(self, callback):
        with self._resource._lock:
            if not self._is_interrupted:
                callback()

    @property
    def is_interrupted(self):
        return self._is_interrupted


class Resource:
    def __init__(self):
        self._lock = Lock()
        self._current_priority = -1
        self._active_handle = None

    def reset(self):
        with self._lock:
            self._current_priority = -1
            self._active_handle = None

    def request(self, with_priority=0, on_taken_away=lambda: None):
        with self._lock:
            if self._active_handle is None:
                self._current_priority = with_priority
                self._active_handle = ResourceHandle(self, on_taken_away)
                return self._active_handle
            elif self._current_priority == with_priority:
                return self._active_handle
            elif self._current_priority > with_priority:
                self._active_handle.interrupt()
                self._current_priority = with_priority
                self._active_handle = ResourceHandle(self, on_taken_away)
                return self._active_handle
            else:
                return None

    def release(self, resource_handle):
        with self._lock:
            if self._active_handle == resource_handle:
                self._active_handle = None
                self._current_priority = -1
