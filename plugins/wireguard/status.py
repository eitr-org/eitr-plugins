#!/usr/bin/env python3
"""WireGuard status as one bounded JSON object for the bar icon and panel."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

TUNNEL_LIMIT = 100
DIRECTORY = Path('/etc/wireguard')
NAME_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,14}\Z')
UUID_RE = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')


def text(value):
    return ''.join(character if character.isprintable() else '?' for character in str(value or ''))[:128]


def state_file():
    base = Path(os.environ.get('XDG_STATE_HOME') or (Path.home() / '.local/state'))
    return base / 'eitr/wireguard-tunnels.json'


def split_terse(line):
    fields = []
    current = []
    escaped = False
    for character in line:
        if escaped:
            current.append(character)
            escaped = False
        elif character == '\\':
            escaped = True
        elif character == ':':
            fields.append(''.join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append('\\')
    fields.append(''.join(current))
    return fields


def format_bytes(amount):
    try:
        value = int(amount)
    except (TypeError, ValueError):
        return '0 B'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024 or unit == 'TiB':
            return f'{value} B' if unit == 'B' else f'{value:.2f} {unit}'
        value /= 1024
    return '0 B'


def parse_wg_show(output):
    """Parse `wg show` (or `wg show all dump`) into non-secret per-interface details."""
    interfaces = {}
    current = None
    peer = None

    def flush_peer(interface_entry, peer_entry):
        if not interface_entry or not peer_entry:
            return
        has_handshake = bool(peer_entry.get('handshake'))
        if has_handshake or not interface_entry.get('endpoint'):
            if peer_entry.get('endpoint'):
                interface_entry['endpoint'] = peer_entry['endpoint']
        if has_handshake or not interface_entry.get('transfer'):
            if peer_entry.get('transfer'):
                interface_entry['transfer'] = peer_entry['transfer']
        if has_handshake:
            interface_entry['handshake'] = peer_entry['handshake']
        if peer_entry.get('allowedIps') and not interface_entry.get('allowedIps'):
            interface_entry['allowedIps'] = peer_entry['allowedIps']

    for raw in (output or '').splitlines():
        if '\t' in raw:
            parts = raw.split('\t')
            name = text(parts[0].strip())
            if not name:
                continue
            entry = interfaces.setdefault(name, {'interface': name, 'endpoint': '', 'transfer': '', 'handshake': '', 'allowedIps': ''})
            if len(parts) >= 8:
                endpoint = parts[3].strip()
                allowed = parts[4].strip()
                handshake = parts[5].strip()
                rx, tx = parts[6].strip(), parts[7].strip()
                flush_peer(entry, {
                    'endpoint': '' if endpoint in ('', '(none)') else text(endpoint),
                    'allowedIps': '' if allowed in ('', '(none)') else text(allowed),
                    'handshake': '' if handshake in ('', '0') else text(handshake),
                    'transfer': f'{format_bytes(rx)} received, {format_bytes(tx)} sent',
                })
            continue
        stripped = raw.strip()
        if not stripped:
            continue
        if not raw[:1].isspace() and stripped.startswith('interface:'):
            flush_peer(current, peer)
            peer = None
            name = text(stripped.partition(':')[2].strip())
            current = interfaces.setdefault(name, {'interface': name, 'endpoint': '', 'transfer': '', 'handshake': '', 'allowedIps': ''}) if name else None
        elif current is not None and stripped.startswith('peer:'):
            flush_peer(current, peer)
            peer = {'endpoint': '', 'transfer': '', 'handshake': '', 'allowedIps': ''}
        elif current is not None and ':' in stripped:
            key, _, value = stripped.partition(':')
            key = key.strip().lower()
            cleaned = text(value.strip())
            target = peer if peer is not None else current
            if key == 'endpoint':
                target['endpoint'] = cleaned
            elif key == 'latest handshake':
                target['handshake'] = cleaned
            elif key == 'transfer':
                target['transfer'] = cleaned
            elif key == 'allowed ips':
                target['allowedIps'] = cleaned
    flush_peer(current, peer)
    return interfaces


def parse_nm_profiles(output):
    """Parse `nmcli -t` connection lines into WireGuard profile records."""
    profiles = []
    for raw in (output or '').splitlines():
        if not raw.strip():
            continue
        fields = split_terse(raw)
        if len(fields) >= 5 and UUID_RE.fullmatch(fields[0]):
            if len(fields) >= 6:
                identifier, kind, active, state, device = fields[:5]
                name = ':'.join(fields[5:])
            else:
                identifier, kind, state, device = fields[:4]
                active = 'yes' if state in ('yes', 'activated') else 'no'
                name = fields[4]
        elif len(fields) >= 5 and UUID_RE.fullmatch(fields[1]):
            name, identifier, kind, state, device = fields[:5]
            active = 'yes' if state in ('yes', 'activated') else 'no'
        elif len(fields) >= 4 and UUID_RE.fullmatch(fields[1]):
            name, identifier, kind, device = fields[:4]
            active = 'yes' if device and device != '--' else 'no'
            state = 'activated' if active == 'yes' else ''
        elif len(fields) >= 2 and UUID_RE.fullmatch(fields[0]):
            identifier, kind = fields[:2]
            name, active, state, device = identifier, 'no', '', ''
        else:
            continue
        if kind != 'wireguard':
            continue
        connected = active == 'yes' or state == 'activated'
        clean_device = '' if device == '--' else text(device)
        profiles.append({
            'id': identifier,
            'name': text(name or identifier),
            'interface': clean_device,
            'connected': connected,
            'state': 'connected' if connected else 'connecting' if state == 'activating' else 'disconnected',
            'endpoint': '',
        })
    return profiles


def parse_ip_links(output):
    names = []
    for line in (output or '').splitlines():
        parts = line.split()
        if parts and NAME_RE.fullmatch(parts[0]):
            names.append(parts[0])
    return names


def saved_wg_quick_profiles():
    records = {}
    try:
        for path in sorted(DIRECTORY.glob('*.conf')):
            if NAME_RE.fullmatch(path.stem):
                records[path.stem] = {'id': path.stem, 'name': path.stem, 'interface': path.stem,
                                      'connected': False, 'state': 'disconnected', 'endpoint': ''}
    except OSError:
        pass
    try:
        items = json.loads(state_file().read_text())
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and NAME_RE.fullmatch(str(item.get('name') or '')):
                    name = item['name']
                    records.setdefault(name, {'id': name, 'name': name, 'interface': name,
                                              'connected': False, 'state': 'disconnected',
                                              'endpoint': text(item.get('endpoint'))})
                    if item.get('endpoint'):
                        records[name]['endpoint'] = text(item.get('endpoint'))
    except (OSError, ValueError):
        pass
    return list(records.values())


def summarize(wg_output, profiles=(), backend='networkmanager', active_links=()):
    """Combine `wg show` output and known profiles into the panel's bounded JSON summary."""
    wg_map = parse_wg_show(wg_output) if isinstance(wg_output, str) else dict(wg_output or {})
    profile_list = parse_nm_profiles(profiles) if isinstance(profiles, str) else list(profiles or [])
    link_set = set(parse_ip_links(active_links) if isinstance(active_links, str) else (active_links or ()))
    matched_interfaces = set()
    tunnels = []

    for profile in profile_list:
        name = text(profile.get('name') or profile.get('id'))
        interface = text(profile.get('interface'))
        live = wg_map.get(interface) or wg_map.get(name)
        if live:
            matched_interfaces.add(live['interface'])
            interface = live['interface']
        elif name in link_set or interface in link_set:
            matched_interfaces.add(interface or name)
            interface = interface or name
        connected = bool(profile.get('connected') or live or (interface and interface in link_set) or name in link_set)
        state = 'connected' if connected else profile.get('state') if profile.get('state') == 'connecting' else 'disconnected'
        tunnels.append({
            'id': text(profile.get('id') or name),
            'name': name,
            'interface': interface if connected else '',
            'connected': connected,
            'state': state,
            'endpoint': text((live or {}).get('endpoint') or profile.get('endpoint')),
            'transfer': text((live or {}).get('transfer')),
            'handshake': text((live or {}).get('handshake')),
        })

    for interface_name, live in wg_map.items():
        if interface_name not in matched_interfaces:
            tunnels.append({
                'id': text(interface_name),
                'name': text(interface_name),
                'interface': text(interface_name),
                'connected': True,
                'state': 'connected',
                'endpoint': text(live.get('endpoint')),
                'transfer': text(live.get('transfer')),
                'handshake': text(live.get('handshake')),
            })
            matched_interfaces.add(interface_name)

    for link_name in sorted(link_set):
        if link_name not in matched_interfaces:
            tunnels.append({
                'id': text(link_name),
                'name': text(link_name),
                'interface': text(link_name),
                'connected': True,
                'state': 'connected',
                'endpoint': '',
                'transfer': '',
                'handshake': '',
            })

    tunnels.sort(key=lambda item: (
        not item['connected'],
        not bool(item['endpoint'] or item['handshake'] or item['transfer']),
        item['name'].casefold(),
    ))
    active = next((item for item in tunnels if item['connected']), None)
    overall = 'connected' if active else 'connecting' if any(item['state'] == 'connecting' for item in tunnels) else 'disconnected'
    return {
        'installed': True,
        'state': overall,
        'backend': backend,
        'tunnels': tunnels[:TUNNEL_LIMIT],
        'tunnelCount': len(tunnels),
        'activeTunnel': active['name'] if active else '',
        'interface': active['interface'] if active else '',
        'endpoint': active['endpoint'] if active else '',
        'transfer': active['transfer'] if active else '',
        'handshake': active['handshake'] if active else '',
    }


def query(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=3, check=False,
                            env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError('Query failed')
    return result.stdout


def nm_active():
    try:
        return subprocess.run(['systemctl', 'is-active', '--quiet', 'NetworkManager.service'],
                              capture_output=True, timeout=3, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def empty_state(installed, state, backend='wg-quick'):
    return {'installed': installed, 'state': state, 'backend': backend, 'tunnels': [], 'tunnelCount': 0,
            'activeTunnel': '', 'interface': '', 'endpoint': '', 'transfer': '', 'handshake': ''}


def read():
    if not shutil.which('wg'):
        return empty_state(False, 'not-installed')
    active = nm_active()
    backend = 'networkmanager' if active else 'wg-quick'
    wg_output = None
    try:
        wg_output = query(['wg', 'show'])
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    if active:
        try:
            nm_output = query(['nmcli', '-t', '-f', 'UUID,TYPE,ACTIVE,STATE,DEVICE,NAME', 'connection', 'show'])
        except (OSError, ValueError, subprocess.SubprocessError):
            if wg_output is None:
                return empty_state(True, 'unavailable', backend)
            nm_output = ''
        return summarize(wg_output or '', nm_output, backend=backend)
    links_output = ''
    if wg_output is None:
        try:
            links_output = query(['ip', '-brief', 'link', 'show', 'type', 'wireguard'])
        except (OSError, ValueError, subprocess.SubprocessError):
            return empty_state(True, 'unavailable', backend)
    return summarize(wg_output or '', saved_wg_quick_profiles(), backend=backend, active_links=links_output)


if __name__ == '__main__':
    if sys.argv[1:] != ['--json']:
        raise SystemExit('Usage: status.py --json')
    print(json.dumps(read(), ensure_ascii=False))
