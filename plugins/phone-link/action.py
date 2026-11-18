#!/usr/bin/env python3
"""Fixed-argv device actions. Clipboard input and errors never enter logs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from connection import Connection, DEVICE, GLib, device_path

PLUGINS = {'send': 'kdeconnect_share', 'clipboard': 'kdeconnect_share',
           'ring': 'kdeconnect_findmyphone', 'ping': 'kdeconnect_ping', 'browse': 'kdeconnect_sftp'}


def run(arguments, timeout=8):
    result = subprocess.run(arguments, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError('command-failed')


def start():
    connection = Connection()
    if connection.running():
        return
    # Only package-owned unit files qualify; no custom user unit is created.
    units = [path for path in Path('/usr/lib/systemd/user').glob('*kdeconnect*.service')
             if path.name in ('kdeconnect.service', 'kdeconnectd.service', 'app-org.kde.kdeconnect.daemon.service')]
    if units:
        run(['systemctl', '--user', 'start', units[0].name])
        return
    daemon = shutil.which('kdeconnectd')
    if not daemon:
        raise RuntimeError('missing')
    subprocess.Popen([daemon], start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def perform(action, identifier='', payload=None, connection=None):
    if action == 'start' and not identifier:
        start()
        return
    if action not in {'pair', 'accept', 'reject', 'unpair', *PLUGINS}:
        raise ValueError('Invalid action.')
    path = device_path(identifier)
    connection = connection or Connection(seconds=10)
    if not connection.running():
        raise RuntimeError('stopped')
    props = connection.properties(path, DEVICE)
    if action in ('accept', 'reject'):
        if not props.get('isPairRequestedByPeer'):
            raise RuntimeError('request-expired')
        connection.call(path, DEVICE, 'acceptPairing' if action == 'accept' else 'cancelPairing')
        return
    if action == 'unpair':
        if not isinstance(payload, dict) or payload.get('confirmed') is not True:
            raise ValueError('Unpair requires confirmation.')
        run(['kdeconnect-cli', '-d', identifier, '--unpair'])
        return
    if not props.get('isReachable'):
        raise RuntimeError('offline')
    if action == 'pair':
        if props.get('isPaired'):
            return
        run(['kdeconnect-cli', '-d', identifier, '--pair'])
        return
    if not props.get('isPaired'):
        raise RuntimeError('unpaired')
    plugins = connection.call(path, DEVICE, 'loadedPlugins')[0]
    if PLUGINS[action] not in plugins:
        raise RuntimeError('unsupported')
    if action in ('ring', 'ping'):
        run(['kdeconnect-cli', '-d', identifier, '--' + action])
    elif action == 'clipboard':
        text = (payload or {}).get('text')
        if not isinstance(text, str) or not text or len(text.encode('utf-8')) > 65536:
            raise ValueError('Empty or oversized clipboard.')
        # Same shareText method as --share-text, without putting private text in argv.
        connection.call(path + '/share', DEVICE + '.share', 'shareText', '(s)', (text,))
    elif action == 'send':
        from portal import choose_files
        title = (payload or {}).get('title', 'Send files')
        files = choose_files(str(title)[:128])
        if not files:
            return 'cancelled'
        # Selection can take minutes; revalidate the phone after the chooser closes.
        connection = Connection(seconds=10)
        props = connection.properties(path, DEVICE)
        if not props.get('isReachable') or not props.get('isPaired'):
            raise RuntimeError('offline')
        if any(not filename.is_file() for filename in files):
            raise ValueError('Choose local files.')
        run(['kdeconnect-cli', '-d', identifier, '--share', *[filename.resolve().as_uri() for filename in files]], timeout=10)
    elif action == 'browse':
        if not connection.call(path + '/sftp', DEVICE + '.sftp', 'mountAndWait', seconds=8)[0]:
            raise RuntimeError('mount-failed')
        mount = connection.call(path + '/sftp', DEVICE + '.sftp', 'mountPoint')[0]
        if not mount or not Path(mount).is_absolute() or not Path(mount).is_dir():
            raise RuntimeError('mount-failed')
        run(['xdg-open', Path(mount).as_uri()])


def main(arguments):
    try:
        if not 1 <= len(arguments) <= 2:
            raise ValueError('Invalid arguments.')
        raw = sys.stdin.buffer.read(70000)
        payload = json.loads(raw) if raw else None
        if payload is not None and not isinstance(payload, dict):
            raise ValueError('Invalid action payload.')
        outcome = perform(arguments[0], arguments[1] if len(arguments) == 2 else '', payload)
        result = {'ok': True, 'cancelled': outcome == 'cancelled'}
    except (GLib.Error, OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError):
        result = {'ok': False}
    print(json.dumps(result), flush=True)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
