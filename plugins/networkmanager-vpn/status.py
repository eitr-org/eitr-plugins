#!/usr/bin/env python3
"""NetworkManager VPN status as one bounded JSON object for the bar icon and panel."""
import json
import os
import re
import shutil
import subprocess
import sys

PROFILE_LIMIT = 100
UUID_RE = re.compile(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z')
PROTOCOL_LABELS = {'openvpn': 'OpenVPN', 'openconnect': 'OpenConnect', 'wireguard': 'WireGuard'}
DETAIL_FIELDS = ('connection.uuid,connection.id,connection.type,vpn.service-type,vpn.data,'
                 'GENERAL.STATE,GENERAL.DEVICES,IP4.ADDRESS,IP4.GATEWAY,IP4.DNS,IP6.ADDRESS')


def text(value):
    return ''.join(character if character.isprintable() else '?' for character in str(value or ''))[:128]


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


def classify_protocol(kind, service_type=''):
    if kind == 'wireguard':
        return 'wireguard'
    if kind != 'vpn':
        return None
    service = (service_type or '').strip().lower()
    if not service or 'openvpn' in service:
        return 'openvpn'
    if 'openconnect' in service:
        return 'openconnect'
    return None


def parse_vpn_endpoint(data_text):
    for item in (data_text or '').split(','):
        key, separator, value = item.partition('=')
        if separator and key.strip() in ('remote', 'gateway'):
            cleaned = value.strip().split()[0] if value.strip() else ''
            if cleaned:
                return text(cleaned)
    return ''


def parse_connections(output):
    """Parse `nmcli -t` connection list output into candidate VPN/WireGuard records."""
    entries = []
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
        if kind not in ('vpn', 'wireguard'):
            continue
        connected = active == 'yes' or state == 'activated'
        entries.append({
            'id': identifier,
            'name': text(name or identifier),
            'kind': kind,
            'connected': connected,
            'state': 'connected' if connected else 'connecting' if state == 'activating' else 'disconnected',
            'interface': '' if device == '--' else text(device),
        })
    return entries


def parse_details(output, fallback_uuid=''):
    """Parse `nmcli -t connection show uuid ...` lines into per-UUID detail dicts."""
    details = {}
    current_id = fallback_uuid if UUID_RE.fullmatch(fallback_uuid or '') else ''

    def ensure(identifier):
        return details.setdefault(identifier, {
            'name': '', 'kind': '', 'serviceType': '', 'state': '', 'interface': '',
            'addresses': [], 'gateway': '', 'dns': [], 'endpoint': ''
        })

    for raw in (output or '').splitlines():
        if not raw.strip() or ':' not in raw:
            continue
        key, _, value = raw.partition(':')
        key = key.strip()
        cleaned = text(value.replace('\\:', ':').replace('\\\\', '\\').strip())
        if key == 'connection.uuid' and UUID_RE.fullmatch(cleaned):
            current_id = cleaned
            ensure(current_id)
            continue
        if not current_id:
            continue
        record = ensure(current_id)
        if key == 'connection.id' and cleaned:
            record['name'] = cleaned
        elif key == 'connection.type' and cleaned:
            record['kind'] = cleaned
        elif key == 'vpn.service-type':
            record['serviceType'] = cleaned
        elif key == 'vpn.data':
            record['endpoint'] = parse_vpn_endpoint(value)
        elif key == 'GENERAL.STATE':
            record['state'] = cleaned
        elif key == 'GENERAL.DEVICES' and cleaned != '--':
            record['interface'] = cleaned
        elif key.startswith(('IP4.ADDRESS', 'IP6.ADDRESS')) and cleaned and cleaned != '--':
            address = cleaned.split('/')[0].strip()
            if address and address not in record['addresses']:
                record['addresses'].append(address)
        elif key == 'IP4.GATEWAY' and cleaned and cleaned != '--':
            record['gateway'] = cleaned
        elif key.startswith('IP4.DNS') and cleaned and cleaned != '--':
            if cleaned not in record['dns']:
                record['dns'].append(cleaned)
    return details


def summarize(connections_output, details_output='', backend='networkmanager'):
    """Reduce `nmcli` connection list and details to bounded JSON for the panel."""
    if backend == 'iwd':
        return empty_state(True, 'iwd', backend='iwd')
    candidates = parse_connections(connections_output) if isinstance(connections_output, str) else list(connections_output or [])
    fallback_id = candidates[0]['id'] if len(candidates) == 1 else ''
    detail_map = parse_details(details_output, fallback_id) if isinstance(details_output, str) else dict(details_output or {})
    profiles = []

    for candidate in candidates:
        identifier = candidate['id']
        detail = detail_map.get(identifier) or {}
        kind = detail.get('kind') or candidate.get('kind') or 'vpn'
        service_type = detail.get('serviceType') or candidate.get('serviceType') or ''
        protocol = classify_protocol(kind, service_type)
        if protocol is None:
            continue
        detail_state = detail.get('state') or ''
        connected = bool(candidate.get('connected') or detail_state == 'activated')
        connecting = not connected and (candidate.get('state') == 'connecting' or detail_state == 'activating')
        addresses = detail.get('addresses') or ([candidate['address']] if candidate.get('address') else [])
        dns_list = detail.get('dns') or ([candidate['dns']] if candidate.get('dns') else [])
        gateway = text(detail.get('gateway') or candidate.get('gateway'))
        endpoint = text(detail.get('endpoint') or candidate.get('endpoint') or gateway)
        profiles.append({
            'id': identifier,
            'name': text(detail.get('name') or candidate.get('name') or identifier),
            'protocol': protocol,
            'typeLabel': PROTOCOL_LABELS[protocol],
            'connected': connected,
            'state': 'connected' if connected else 'connecting' if connecting else 'disconnected',
            'interface': text(detail.get('interface') or candidate.get('interface')) if connected else '',
            'address': text(addresses[0]) if addresses else '',
            'endpoint': endpoint,
            'gateway': gateway,
            'dns': text(', '.join(dns_list)),
        })

    profiles.sort(key=lambda item: (not item['connected'], item['name'].casefold()))
    active = next((item for item in profiles if item['connected']), None)
    overall = 'connected' if active else 'connecting' if any(item['state'] == 'connecting' for item in profiles) else 'disconnected'
    return {
        'installed': True,
        'state': overall,
        'backend': backend,
        'profiles': profiles[:PROFILE_LIMIT],
        'profileCount': len(profiles),
        'activeProfile': active['name'] if active else '',
        'protocol': active['typeLabel'] if active else '',
        'interface': active['interface'] if active else '',
        'address': active['address'] if active else '',
        'endpoint': active['endpoint'] if active else '',
        'gateway': active['gateway'] if active else '',
        'dns': active['dns'] if active else '',
    }


def empty_state(installed, state, backend='networkmanager'):
    return {'installed': installed, 'state': state, 'backend': backend, 'profiles': [], 'profileCount': 0,
            'activeProfile': '', 'protocol': '', 'interface': '', 'address': '', 'endpoint': '', 'gateway': '', 'dns': ''}


def query(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=3, check=False,
                            env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError('NetworkManager query failed')
    return result.stdout


def nm_active():
    try:
        return subprocess.run(['systemctl', 'is-active', '--quiet', 'NetworkManager.service'],
                              capture_output=True, timeout=3, check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def read():
    if not shutil.which('nmcli'):
        return empty_state(False, 'not-installed', backend='unavailable')
    if not nm_active():
        return empty_state(True, 'iwd', backend='iwd')
    try:
        connections_output = query(['nmcli', '-t', '-f', 'UUID,TYPE,ACTIVE,STATE,DEVICE,NAME', 'connection', 'show'])
    except (OSError, ValueError, subprocess.SubprocessError):
        return empty_state(True, 'unavailable', backend='networkmanager')
    candidates = parse_connections(connections_output)
    details_output = ''
    if candidates:
        uuids = [item['id'] for item in candidates[:PROFILE_LIMIT]]
        try:
            details_output = query(['nmcli', '-t', '-f', DETAIL_FIELDS, 'connection', 'show', 'uuid', *uuids])
        except (OSError, ValueError, subprocess.SubprocessError):
            details_output = ''
    return summarize(candidates, details_output, backend='networkmanager')


if __name__ == '__main__':
    if sys.argv[1:] != ['--json']:
        raise SystemExit('Usage: status.py --json')
    print(json.dumps(read(), ensure_ascii=False))
