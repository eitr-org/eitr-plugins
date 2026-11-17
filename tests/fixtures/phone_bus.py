"""KDE Connect and file chooser stand-ins, used only inside dbus-run-session."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import threading

import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib

PLUGIN = Path(sys.argv[1])
sys.path.insert(0, str(PLUGIN))
from connection import Connection, DEVICE, ROOT, SERVICE
import action
import portal
import status


bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
registrations = []
charge = 80
incoming = True
shared = []
selection = []
cancel = False


def own(name, method='RequestName'):
    values = GLib.Variant('(su)', (name, 0)) if method == 'RequestName' else GLib.Variant('(s)', (name,))
    bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                  method, values, None, Gio.DBusCallFlags.NONE, 1000, None)


def register(path, xml, called=None, property_value=None):
    interface = Gio.DBusNodeInfo.new_for_xml('<node>' + xml + '</node>').interfaces[0]
    registrations.append(bus.register_object(path, interface, called, property_value, None))


def daemon(_bus, _sender, _path, _interface, _method, parameters, invocation):
    reachable, paired = parameters.unpack()
    invocation.return_value(GLib.Variant('(as)', (['phone'] if paired else ['phone', 'request'],)))


def device_call(_bus, _sender, _path, _interface, method, _parameters, invocation):
    global incoming
    if method == 'loadedPlugins':
        invocation.return_value(GLib.Variant('(as)', (['kdeconnect_battery', 'kdeconnect_share', 'kdeconnect_sftp'],)))
    else:
        incoming = False
        invocation.return_value(None)


def device_property(_bus, _sender, path, _interface, name):
    is_phone = path.endswith('/phone')
    values = {'name': ('s', 'Phone' if is_phone else 'New phone'), 'type': ('s', 'phone'),
              'isReachable': ('b', True), 'isPaired': ('b', is_phone),
              'isPairRequested': ('b', False), 'isPairRequestedByPeer': ('b', incoming and not is_phone),
              'verificationKey': ('s', '123456')}
    kind, value = values[name]
    return GLib.Variant(kind, value)


def battery_property(_bus, _sender, _path, _interface, name):
    return GLib.Variant('i' if name == 'charge' else 'b', charge if name == 'charge' else True)


def share(_bus, _sender, _path, _interface, _method, parameters, invocation):
    shared.append(parameters.unpack()[0])
    invocation.return_value(None)


def open_files(_bus, sender, _path, _interface, _method, parameters, invocation):
    token = parameters.unpack()[2]['handle_token']
    handle = '/org/freedesktop/portal/desktop/request/' + sender.lstrip(':').replace('.', '_') + '/' + token
    invocation.return_value(GLib.Variant('(o)', (handle,)))
    def respond():
        bus.emit_signal(sender, handle, 'org.freedesktop.portal.Request', 'Response',
                        GLib.Variant('(ua{sv})', (1 if cancel else 0, {'uris': GLib.Variant('as', selection)})))
        return GLib.SOURCE_REMOVE
    GLib.timeout_add(30, respond)


register(ROOT, '''<interface name="org.kde.kdeconnect.daemon">
 <method name="devices"><arg type="b" direction="in"/><arg type="b" direction="in"/><arg type="as" direction="out"/></method>
 <property name="pairingRequests" type="as" access="read"/>
</interface>''', daemon, lambda *_arguments: GLib.Variant('as', ['request'] if incoming else []))
device_xml = '''<interface name="org.kde.kdeconnect.device">
 <method name="loadedPlugins"><arg type="as" direction="out"/></method>
 <method name="acceptPairing"/><method name="cancelPairing"/>
 <property name="name" type="s" access="read"/><property name="type" type="s" access="read"/>
 <property name="isReachable" type="b" access="read"/><property name="isPaired" type="b" access="read"/>
 <property name="isPairRequested" type="b" access="read"/><property name="isPairRequestedByPeer" type="b" access="read"/>
 <property name="verificationKey" type="s" access="read"/>
</interface>'''
for identifier in ('phone', 'request'):
    register(ROOT + '/devices/' + identifier, device_xml, device_call, device_property)
register(ROOT + '/devices/phone/battery', '''<interface name="org.kde.kdeconnect.device.battery">
 <property name="charge" type="i" access="read"/><property name="isCharging" type="b" access="read"/>
 <property name="hasBattery" type="b" access="read"/>
</interface>''', None, battery_property)
register(ROOT + '/devices/phone/share', '''<interface name="org.kde.kdeconnect.device.share">
 <method name="shareText"><arg type="s" direction="in"/></method>
</interface>''', share)
register('/org/freedesktop/portal/desktop', '''<interface name="org.freedesktop.portal.FileChooser">
 <method name="OpenFile"><arg type="s" direction="in"/><arg type="s" direction="in"/>
 <arg type="a{sv}" direction="in"/><arg type="o" direction="out"/></method>
</interface>''', open_files)
own(SERVICE)
own('org.freedesktop.portal.Desktop')
loop = GLib.MainLoop()
thread = threading.Thread(target=loop.run, daemon=True)
thread.start()


def next_state(process, predicate):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        for _attempt in range(8):
            assert selector.select(4), 'Timed out waiting for a D-Bus update'
            state = json.loads(process.stdout.readline())
            if predicate(state):
                return state
    raise AssertionError('Expected state was never received')


try:
    with tempfile.TemporaryDirectory() as temporary:
        folder = Path(temporary)
        stub = folder / 'kdeconnect-cli'
        stub.write_text('#!/bin/sh\nexit 99\n')
        stub.chmod(0o700)
        os.environ['PATH'] = str(folder) + os.pathsep + os.environ['PATH']
        result = status.read()
        assert result['state'] == 'ready', result
        assert result['devices'][0]['incoming'], result
        assert result['devices'][1]['battery'] == 80, result
        action.perform('clipboard', 'phone', {'text': 'private\ntext'})
        assert shared == ['private\ntext'], shared
        action.perform('reject', 'request')
        assert not incoming
        file = folder / 'file with spaces.txt'
        file.write_text('fixture')
        selection = [file.as_uri()]
        assert portal.choose_files('Fixture') == [file]
        cancel = True
        assert portal.choose_files('Fixture') == []
        watcher = subprocess.Popen([sys.executable, str(PLUGIN / 'status.py'), '--watch'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            next_state(watcher, lambda state: state['state'] == 'ready')
            charge = 79
            bus.emit_signal(None, ROOT + '/devices/phone/battery', DEVICE + '.battery', 'refreshed',
                            GLib.Variant('(bi)', (True, charge)))
            next_state(watcher, lambda state: any(device['battery'] == 79 for device in state['devices']))
            incoming = True
            bus.emit_signal(None, ROOT + '/devices/request', DEVICE, 'pairStateChanged', GLib.Variant('(i)', (2,)))
            next_state(watcher, lambda state: any(device['incoming'] for device in state['devices']))
            own(SERVICE, 'ReleaseName')
            next_state(watcher, lambda state: state['state'] == 'stopped')
            own(SERVICE)
            next_state(watcher, lambda state: state['state'] == 'ready')
        finally:
            watcher.terminate()
            watcher.communicate(timeout=3)
    print('PHONE_PRIVATE_BUS_OK')
finally:
    loop.quit()
    thread.join(timeout=2)
    for registration in registrations:
        bus.unregister_object(registration)
