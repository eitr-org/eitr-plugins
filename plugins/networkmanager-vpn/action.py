#!/usr/bin/env python3
"""Explicit NetworkManager VPN actions; credentials never enter diagnostics or command arguments."""
import html
from pathlib import Path
import re
import subprocess
import sys

from runtime import choose, collect, launch, open_settings, open_terminal, run, Step, wait_for_escape
from eitr_vpn import wireguard_summary

WIREGUARD = Path(__file__).parent.name == 'wireguard'
UUID_RE = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')
GUIDE = ('The active WiFi backend is iwd or NetworkManager is unavailable. VPN profiles need '
         'NetworkManager. Choose Settings > Connections > Wi-Fi > WiFi backend, then reboot. '
         'The saved choice leaves the current connection running.')
BACKGROUND = ('up', 'down', 'connect', 'disconnect', 'open-settings')


def notify(message):
    subprocess.run(['notify-send', '--app-name=NetworkManager VPN', '--', 'NetworkManager VPN', html.escape(message)],
                   check=False, timeout=10)


def nm_active():
    return subprocess.run(['systemctl', 'is-active', '--quiet', 'NetworkManager.service'],
                          capture_output=True, timeout=10).returncode == 0


def profiles():
    output = run(['nmcli', '-t', '-f', 'UUID,TYPE', 'connection', 'show'])
    entries = []
    for line in output.splitlines():
        identifier, separator, kind = line.partition(':')
        if separator and kind in ('vpn', 'wireguard') and UUID_RE.fullmatch(identifier):
            name = run(['nmcli', '-g', 'connection.id', 'connection', 'show', 'uuid', identifier]).strip()
            entries.append((name + ' · ' + identifier, identifier))
    return entries


def import_profile(active):
    if not active:
        print(GUIDE)
        open_settings()
        wait_for_escape()
        return
    answer = collect('Import VPN configuration', [Step('file', 'Configuration file',
                     description='Enter the full path (.ovpn or .conf); Enter confirms and Esc cancels.')])
    path = Path(answer['file']).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix not in ('.ovpn', '.conf') or path.stat().st_size > 1024 * 1024:
        raise ValueError('Invalid configuration file.')
    kind = 'wireguard' if path.suffix == '.conf' else 'openvpn'
    if kind == 'wireguard':
        wireguard_summary(path.stem, path.read_text())
    output = run(['nmcli', 'connection', 'import', '--temporary', 'type', kind, 'file', str(path)])
    identifiers = re.findall(r'\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b', output)
    if len(identifiers) != 1:
        raise RuntimeError('Cannot identify imported profile.')
    try:
        run(['nmcli', 'connection', 'modify', 'uuid', identifiers[0], 'connection.autoconnect', 'no'])
    except (RuntimeError, OSError, subprocess.SubprocessError):
        run(['nmcli', 'connection', 'delete', 'uuid', identifiers[0]])
        raise
    print('Imported; automatic connection is disabled.')
    wait_for_escape()


def switch_profile(direction, identifier):
    if not UUID_RE.fullmatch(identifier):
        raise ValueError('Invalid profile identifier.')
    kind = run(['nmcli', '-g', 'connection.type', 'connection', 'show', 'uuid', identifier]).strip()
    if kind not in ('vpn', 'wireguard'):
        raise ValueError('Only VPN connections are supported.')
    step = 'up' if direction in ('up', 'connect') else 'down'
    run(['nmcli', '--wait', '30', 'connection', step, 'uuid', identifier])


def background(arguments):
    """Panel actions: connect/disconnect via nmcli, or open Settings when on iwd."""
    action = arguments[0]
    try:
        if action == 'open-settings':
            open_settings()
            return
        if not nm_active():
            open_settings()
            return
        if len(arguments) == 2 and action in ('up', 'down', 'connect', 'disconnect'):
            switch_profile(action, arguments[1])
        else:
            raise ValueError('Unknown action.')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        notify(str(error) if isinstance(error, RuntimeError) else 'The VPN action failed.')
        raise SystemExit(1)


def main(action):
    if action == 'open-settings':
        open_settings()
        return
    active = nm_active()
    if not active:
        print(GUIDE)
        open_settings()
        wait_for_escape()
        return
    if action == 'import':
        import_profile(active)
        return
    entries = profiles()
    if action == 'status':
        for name, identifier in entries:
            state = run(['nmcli', '-g', 'GENERAL.STATE', 'connection', 'show', 'uuid', identifier]).strip()
            print(name + ' · ' + (state or 'disconnected'))
        if not entries:
            print('No saved VPN profiles.')
        wait_for_escape()
        return
    identifier = choose('Choose VPN profile', entries)
    run(['nmcli', '--wait', '30', 'connection', action, 'uuid', identifier])


if __name__ == '__main__':
    if sys.argv[1:2] and (sys.argv[1] == 'open-settings' or (len(sys.argv) == 3 and sys.argv[1] in BACKGROUND)) and '--terminal' not in sys.argv:
        background(sys.argv[1:])
    else:
        launch(main)
