#!/usr/bin/env python3
"""Explicit WireGuard actions; credentials never enter diagnostics or command arguments."""
import html
import json
from pathlib import Path
import re
import subprocess
import sys

import status as wireguard_status
from runtime import choose, collect, launch, open_terminal, run, Step, wait_for_escape
from eitr_vpn import wireguard_summary

WIREGUARD = Path(__file__).parent.name == 'wireguard'
NAME_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,14}\Z')
UUID_RE = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')
BACKGROUND = ('up', 'down', 'connect', 'disconnect', 'remove')


def notify(message):
    subprocess.run(['notify-send', '--app-name=WireGuard', '--', 'WireGuard', html.escape(message)],
                   check=False, timeout=10)


def nm_active():
    return subprocess.run(['systemctl', 'is-active', '--quiet', 'NetworkManager.service'],
                          capture_output=True, timeout=10).returncode == 0


def record_saved_tunnel(name, summary_text=''):
    parts = [part.strip() for part in str(summary_text or '').split('·')]
    endpoint = parts[1] if len(parts) >= 2 and parts[1] != '—' else ''
    path = wireguard_status.state_file()
    try:
        items = json.loads(path.read_text()) if path.is_file() else []
        if not isinstance(items, list):
            items = []
        items = [item for item in items if isinstance(item, dict) and item.get('name') != name]
        items.append({'name': name, 'endpoint': endpoint})
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(json.dumps(items))
    except OSError:
        pass


def forget_saved_tunnel(name):
    path = wireguard_status.state_file()
    try:
        if not path.is_file():
            return
        items = json.loads(path.read_text())
        if isinstance(items, list):
            path.write_text(json.dumps([item for item in items if isinstance(item, dict) and item.get('name') != name]))
    except (OSError, ValueError):
        pass


def profiles():
    output = run(['nmcli', '-t', '-f', 'UUID,TYPE', 'connection', 'show'])
    entries = []
    for line in output.splitlines():
        identifier, separator, kind = line.partition(':')
        if separator and kind == 'wireguard' and UUID_RE.fullmatch(identifier):
            name = run(['nmcli', '-g', 'connection.id', 'connection', 'show', 'uuid', identifier]).strip()
            entries.append((name + ' · ' + identifier, identifier))
    return entries


def import_profile(active):
    answer = collect('Import VPN configuration', [Step('file', 'Configuration file',
                     description='Enter the full path; Enter confirms and Esc cancels.')])
    path = Path(answer['file']).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix != '.conf' or path.stat().st_size > 1024 * 1024:
        raise ValueError('Invalid configuration file.')
    content = path.read_text()
    summary = wireguard_summary(path.stem, content)
    if not active:
        print('iwd: importing needs the administrator password. The root-owned config is saved '
              'under /etc/wireguard with mode 0600. Existing configs are never overwritten.')
        choose('Save WireGuard configuration', [('Save ' + path.stem + ' under /etc/wireguard', True)])
        run(['sudo', '/usr/lib/eitr/eitr-system', 'vpn-import'], input=json.dumps({
            'name': path.stem, 'kind': 'wireguard', 'content': content,
            'backend': 'wg-quick', 'connect': False}), timeout=120)
        record_saved_tunnel(path.stem, summary)
        print('Imported; the tunnel is disconnected.')
        wait_for_escape()
        return
    output = run(['nmcli', 'connection', 'import', '--temporary', 'type', 'wireguard', 'file', str(path)])
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


def verify_nm_wireguard(identifier):
    if not UUID_RE.fullmatch(identifier):
        raise ValueError('Invalid tunnel identifier.')
    kind = run(['nmcli', '-g', 'connection.type', 'connection', 'show', 'uuid', identifier]).strip()
    if kind != 'wireguard':
        raise ValueError('Only WireGuard connections are supported.')


def remove_tunnel(target, active):
    if active:
        verify_nm_wireguard(target)
        run(['nmcli', 'connection', 'delete', 'uuid', target])
    else:
        if not NAME_RE.fullmatch(target):
            raise ValueError('Invalid tunnel name.')
        run(['pkexec', '/usr/bin/rm', '-f', '--', '/etc/wireguard/' + target + '.conf'], timeout=120)
        forget_saved_tunnel(target)


def switch_tunnel(direction, target, active):
    step = 'up' if direction in ('up', 'connect') else 'down'
    if active:
        verify_nm_wireguard(target)
        run(['nmcli', '--wait', '30', 'connection', step, 'uuid', target])
    else:
        if not NAME_RE.fullmatch(target):
            raise ValueError('Invalid tunnel name.')
        run(['pkexec', '/usr/bin/wg-quick', step, '/etc/wireguard/' + target + '.conf'], timeout=120)


def background(arguments):
    """Panel actions: connect, disconnect and remove use nmcli or pkexec without a terminal."""
    action = arguments[0]
    try:
        if len(arguments) != 2 or action not in BACKGROUND:
            raise ValueError('Unknown action.')
        target = arguments[1]
        active = nm_active()
        if action == 'remove':
            remove_tunnel(target, active)
        else:
            switch_tunnel(action, target, active)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        notify(str(error) if isinstance(error, RuntimeError) else 'The WireGuard action failed.')
        raise SystemExit(1)


def main(action):
    active = nm_active()
    if action == 'import':
        import_profile(active)
        return
    if active:
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
        if action == 'remove':
            choose('Remove WireGuard tunnel', [('Remove ' + identifier, True)])
            remove_tunnel(identifier, True)
            return
        run(['nmcli', '--wait', '30', 'connection', action, 'uuid', identifier])
    else:
        print('iwd: wg-quick needs the administrator password. Import a config first; '
              'then enter its profile name (the .conf filename without its suffix).')
        if action == 'status':
            print(run(['ip', '-brief', 'link', 'show', 'type', 'wireguard']) or 'No active WireGuard interfaces.')
            wait_for_escape()
            return
        name = collect('WireGuard tunnel', [Step('name', 'Profile name',
                       validator=lambda name: bool(NAME_RE.fullmatch(name)))])['name']
        if action == 'remove':
            choose('Remove WireGuard tunnel', [('Remove ' + name, True)])
            remove_tunnel(name, False)
            return
        run(['pkexec', '/usr/bin/wg-quick', action, '/etc/wireguard/' + name + '.conf'], timeout=120)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] in BACKGROUND and '--terminal' not in sys.argv:
        background(sys.argv[1:])
    else:
        launch(main)
