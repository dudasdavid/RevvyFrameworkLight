# SPDX-License-Identifier: GPL-3.0-only

from revvy.mcu.rrrc_control import RevvyControl


class PortCollection:
    def __init__(self, ports):
        self._ports = list(ports)
        self._alias_map = {}

    @property
    def aliases(self):
        return self._alias_map

    def __getitem__(self, item):
        if type(item) is str:
            item = self._alias_map[item]

        return self._ports[item - 1]

    def __iter__(self):
        return self._ports.__iter__()


class PortHandler:
    def __init__(self, interface: RevvyControl, configs: dict, drivers: dict, amount: int, supported: dict):
        self._drivers = drivers
        self._configurations = configs
        self._types = supported
        self._port_count = amount
        self._ports = {i: PortInstance(i, interface, self) for i in range(1, self.port_count + 1)}

    def __getitem__(self, port_idx):
        return self._ports[port_idx]

    def __iter__(self):
        return self._ports.values().__iter__()

    @property
    def available_types(self):
        """List of names of the supported drivers"""
        return self._types.values()

    @property
    def port_count(self):
        return self._port_count

    def reset(self):
        for port in self:
            port.uninitialize()

    def _set_port_type(self, port, port_type): raise NotImplementedError

    def configure_port(self, port, config_name):
        config = self._configurations[config_name]
        new_driver_name = config['driver']
        print('PortInstance: Configuring port {} to {} ({})'.format(port.id, config_name, new_driver_name))
        self._set_port_type(port.id, self._types[new_driver_name])
        return self._drivers[new_driver_name](port, config['config'])


class PortInstance:
    def __init__(self, port_idx, interface: RevvyControl, owner: PortHandler):
        self._port_idx = port_idx
        self._owner = owner
        self._interface = interface
        self._driver = owner._drivers["NotConfigured"](self, None)
        self._config_changed_callback = lambda port, cfg_name: None
        self._configuration = "NotConfigured"

    def on_config_changed(self, callback):
        self._config_changed_callback = callback

    def _notify_config_changed(self, config_name):
        self._config_changed_callback(self, config_name)

    def configure(self, config_name):
        if not (self._configuration == "NotConfigured" and config_name == "NotConfigured"):
            self._configuration = config_name
            self._notify_config_changed("NotConfigured")  # temporarily disable reading port
            self._driver = self._owner.configure_port(self, config_name)
            self._notify_config_changed(config_name)

        return self._driver

    def uninitialize(self):
        self.configure("NotConfigured")

    @property
    def interface(self):
        return self._interface

    @property
    def id(self):
        return self._port_idx

    def __getattr__(self, name):
        return self._driver.__getattribute__(name)
