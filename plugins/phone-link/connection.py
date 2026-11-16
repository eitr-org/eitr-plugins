"""Bounded, non-activating access to KDE Connect's session D-Bus API."""
import re
import time

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

SERVICE = 'org.kde.kdeconnect'
ROOT = '/modules/kdeconnect'
DEVICE = SERVICE + '.device'
IDENTIFIER = re.compile(r'[A-Za-z0-9_]{1,128}\Z')


def device_path(identifier):
    if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
        raise ValueError('Invalid device identifier.')
    return ROOT + '/devices/' + identifier


class Connection:
    def __init__(self, seconds=6):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.deadline = time.monotonic() + seconds

    def call(self, path, interface, method, signature=None, values=(), seconds=1, destination=SERVICE):
        remaining = min(seconds, self.deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError('KDE Connect did not answer in time.')
        parameters = GLib.Variant(signature, values) if signature else None
        return self.bus.call_sync(destination, path, interface, method, parameters, None,
                                  Gio.DBusCallFlags.NO_AUTO_START, max(1, int(remaining * 1000)), None).unpack()

    def running(self):
        return self.call('/org/freedesktop/DBus', 'org.freedesktop.DBus', 'NameHasOwner',
                         '(s)', (SERVICE,), destination='org.freedesktop.DBus')[0]

    def properties(self, path, interface):
        return self.call(path, 'org.freedesktop.DBus.Properties', 'GetAll', '(s)', (interface,))[0]
