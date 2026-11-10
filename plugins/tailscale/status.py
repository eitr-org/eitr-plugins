#!/usr/bin/env python3
"""Tailscale status as one bounded JSON object for the bar icon and panel."""
import getpass
import json
import os
import shutil
import subprocess
import sys

PEER_LIMIT = 200
# ipnstate.TaildropTargetAvailable in `tailscale status --json`.
TAILDROP_AVAILABLE = 1
STATES = {'Running': 'connected', 'Stopped': 'disconnected', 'NeedsLogin': 'signed-out',
          'NeedsMachineAuth': 'needs-approval', 'Starting': 'starting', 'NoState': 'starting'}


def query(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=3, check=False,
                            env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise ValueError('Tailscale query failed')
    return json.loads(result.stdout)


def text(value):
    return ''.join(character if character.isprintable() else '?' for character in str(value or ''))[:128]


def connection(peer):
    if not peer.get('Online'):
        return 'offline'
    if peer.get('Active'):
        return 'direct' if peer.get('CurAddr') else 'relayed' if peer.get('Relay') else 'idle'
    return 'idle'


def can_receive(peer, own_user):
    target = peer.get('TaildropTarget')
    if isinstance(target, int) and not isinstance(target, bool):
        return target == TAILDROP_AVAILABLE
    return peer.get('Online') is True and own_user is not None and peer.get('UserID') == own_user


def peer_entry(peer, own_user):
    addresses = [text(address) for address in peer.get('TailscaleIPs') or []]
    name = peer.get('HostName') or (peer.get('DNSName') or '').split('.')[0] or (addresses[0] if addresses else '')
    return {'name': text(name), 'address': addresses[0] if addresses else '', 'os': text(peer.get('OS')),
            'online': peer.get('Online') is True, 'connection': connection(peer),
            'taildrop': bool(addresses) and can_receive(peer, own_user)}


def summarize(status, operator_user, user):
    """Reduce `tailscale status --json` and the operator preference to what the panel shows."""
    backend = status.get('BackendState')
    local = status.get('Self') or {}
    own_user = local.get('UserID')
    peers = [peer_entry(peer, own_user) for peer in (status.get('Peer') or {}).values() if isinstance(peer, dict)]
    peers.sort(key=lambda peer: (not peer['online'], peer['name'].casefold()))
    return {'installed': True, 'state': STATES.get(backend, 'unavailable'),
            'operator': operator_user == user if operator_user is not None else None,
            'device': text(local.get('HostName')),
            'addresses': [text(address) for address in status.get('TailscaleIPs') or []],
            'network': text((status.get('CurrentTailnet') or {}).get('Name')),
            'peers': peers[:PEER_LIMIT], 'peerCount': len(peers)}


def operator():
    try:
        return query(['tailscale', 'debug', 'prefs']).get('OperatorUser') or ''
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None


def read():
    if not shutil.which('tailscale'):
        return {'installed': False, 'state': 'not-installed', 'operator': None, 'peers': [], 'addresses': []}
    try:
        status = query(['tailscale', 'status', '--json'])
        if not isinstance(status, dict):
            raise ValueError('Unexpected status')
    except (OSError, ValueError, subprocess.SubprocessError):
        return {'installed': True, 'state': 'unavailable', 'operator': None, 'peers': [], 'addresses': []}
    return summarize(status, operator(), getpass.getuser())


if __name__ == '__main__':
    if sys.argv[1:] != ['--json']:
        raise SystemExit('Usage: status.py --json')
    print(json.dumps(read(), ensure_ascii=False))
