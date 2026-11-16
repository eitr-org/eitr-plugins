#!/usr/bin/env python3
"""JSON snapshots and a signal-driven stream; never starts KDE Connect implicitly."""
import json
import shutil
import sys
import time

from connection import Connection, DEVICE, GLib, Gio, ROOT, SERVICE, device_path

DEVICE_LIMIT = 8
LINE_LIMIT = 4000


def clean_name(value):
    return ''.join(character if character.isprintable() else ' ' for character in str(value))[:64]


def device_entry(connection, identifier):
    path = device_path(identifier)
    props = connection.properties(path, DEVICE)
    reachable = props.get('isReachable') is True
    paired = props.get('isPaired') is True
    entry = dict(id=identifier, name=clean_name(props.get('name') or identifier),
                 type=props.get('type') if props.get('type') in ('phone', 'tablet', 'desktop', 'laptop', 'tv') else 'phone',
                 reachable=reachable, paired=paired,
                 incoming=props.get('isPairRequestedByPeer') is True,
                 outgoing=props.get('isPairRequested') is True,
                 verification=clean_name(props.get('verificationKey') or ''),
                 battery=None, charging=False, plugins=[])
    if reachable and paired:
        plugins = connection.call(path, DEVICE, 'loadedPlugins')[0]
        entry['plugins'] = [plugin for plugin in plugins if plugin in (
            'kdeconnect_share', 'kdeconnect_findmyphone', 'kdeconnect_ping', 'kdeconnect_sftp')]
        if 'kdeconnect_battery' in plugins:
            try:
                battery = connection.properties(path + '/battery', DEVICE + '.battery')
                charge = battery.get('charge')
                if type(charge) is int and 0 <= charge <= 100 and battery.get('hasBattery', True):
                    entry.update(battery=charge, charging=battery.get('isCharging') is True)
            except (GLib.Error, TimeoutError):
                pass
    return entry


def read(connection=None):
    if not shutil.which('kdeconnect-cli'):
        return dict(state='missing', devices=[], total=0)
    connection = connection or Connection()
    if not connection.running():
        return dict(state='stopped', devices=[], total=0)
    identifiers = connection.call(ROOT, SERVICE + '.daemon', 'devices', '(bb)', (False, False))[0]
    connected = connection.call(ROOT, SERVICE + '.daemon', 'devices', '(bb)', (True, True))[0]
    requests = connection.properties(ROOT, SERVICE + '.daemon').get('pairingRequests', [])
    prioritized = list(dict.fromkeys([*requests, *connected, *identifiers]))
    devices = []
    failed = False
    for identifier in prioritized[:DEVICE_LIMIT]:
        try:
            devices.append(device_entry(connection, identifier))
        except (GLib.Error, ValueError, TimeoutError):
            failed = True
    devices.sort(key=lambda device: (not device['incoming'], not (device['paired'] and device['reachable']),
                                     not device['paired'], device['name'].casefold(), device['id']))
    return dict(state='ready', devices=devices, total=len(identifiers), partial=failed)


def snapshot(connection=None):
    try:
        return read(connection)
    except (GLib.Error, OSError, TimeoutError, ValueError):
        return dict(state='unavailable', devices=[], total=0)


def encode(state):
    """Keep complete JSON inside the host's 4096-byte line transport."""
    state = {**state, 'devices': list(state['devices'])}
    while True:
        line = json.dumps(state, ensure_ascii=False, separators=(',', ':'))
        if len(line.encode('utf-8')) <= LINE_LIMIT:
            return line
        state['devices'].pop()


def watch():
    connection = Connection()
    loop = GLib.MainLoop()
    pending = None

    def emit():
        nonlocal pending
        pending = None
        connection.deadline = time.monotonic() + 6
        print(encode(snapshot(connection)), flush=True)
        return GLib.SOURCE_REMOVE

    def changed(_bus, _sender, path, interface, _member, parameters):
        nonlocal pending
        if interface == 'org.freedesktop.DBus' and parameters.unpack()[0] != SERVICE:
            return
        if interface != 'org.freedesktop.DBus' and not path.startswith(ROOT):
            return
        if pending is None:
            pending = GLib.timeout_add(150, emit)

    subscriptions = [connection.bus.signal_subscribe(
        SERVICE, None, None, None, None, Gio.DBusSignalFlags.NONE, changed),
        connection.bus.signal_subscribe('org.freedesktop.DBus', 'org.freedesktop.DBus',
            'NameOwnerChanged', '/org/freedesktop/DBus', SERVICE, Gio.DBusSignalFlags.NONE, changed)]
    try:
        emit()
        loop.run()
    finally:
        if pending is not None:
            GLib.source_remove(pending)
        for subscription in subscriptions:
            connection.bus.signal_unsubscribe(subscription)


if __name__ == '__main__':
    if sys.argv[1:] == ['--watch']:
        watch()
    elif sys.argv[1:] == ['--json']:
        print(encode(snapshot()))
    else:
        raise SystemExit('Use --json or --watch.')
