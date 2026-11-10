#!/usr/bin/env python3
"""Tailscale actions for the bar panel and Walker rows.

Connect, Disconnect, Send to a device and Open received files run without a terminal
from the panel; a step that needs one (a password, a browser sign-in) reopens the
action in Eitr's task terminal. Installing Tailscale stays with Eitr's reviewed
Remote Access setup."""
import getpass
import html
import ipaddress
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import urllib.parse

import status as tailscale_status
from taildrop import INBOX, announce, fetch, printable
from runtime import ROOT, choose, collect, launch, open_terminal, run, Step, wait_for_escape

CORE_SETUP = ROOT / 'walker/scripts/actions/system/remote-access.py'
BACKGROUND = ('connect', 'disconnect', 'send-to', 'open-folder')
SEND_TIMEOUT = 300


def notify(message):
    subprocess.run(['notify-send', '--app-name=Tailscale', '--', 'Tailscale', html.escape(message)],
                   check=False, timeout=10)


def own_online_peers(status):
    own_id = (status.get('Self') or {}).get('UserID')
    if not own_id:
        return []
    entries = []
    for peer in (status.get('Peer') or {}).values():
        addresses = peer.get('TailscaleIPs') or []
        if peer.get('Online') is True and peer.get('UserID') == own_id and addresses:
            entries.append((peer.get('HostName') or peer.get('DNSName') or addresses[0], addresses[0]))
    return entries


def auth_url(line):
    for value in re.findall(r'https://[^\s]+', line):
        parsed = urllib.parse.urlsplit(value)
        if parsed.hostname in ('login.tailscale.com', 'controlplane.tailscale.com') and not parsed.username and parsed.port in (None, 443):
            return value
    return None


def open_detached(arguments):
    subprocess.Popen([str(ROOT / 'walker/bin/app-launch'), *arguments], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def allow_operator():
    """Let this account control Tailscale without sudo; asks first, runs in a terminal."""
    user = getpass.getuser()
    print('Tailscale needs your administrator password once to let this account connect, '
          'disconnect and use Taildrop without sudo. This changes the Tailscale configuration.')
    print('Command: sudo tailscale set --operator=' + user)
    choose('Allow this account to control Tailscale?', [('Run the displayed command', True)])
    subprocess.run(['sudo', 'tailscale', 'set', '--operator=' + user], check=True, timeout=120)


def login():
    """Stream `tailscale login` and open its sign-in page; login resets unnamed settings, so the operator is kept."""
    with subprocess.Popen(['tailscale', 'login', '--operator=' + getpass.getuser()], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
        opened = set()
        for line in process.stdout:
            print(line, end='', flush=True)
            url = auth_url(line)
            if url and url not in opened:
                open_detached(['xdg-open', url])
                opened.add(url)
        if process.wait():
            raise RuntimeError('Tailscale sign-in failed. Try again from the Tailscale panel.')


def switch(action):
    """`tailscale up` names the operator, or it refuses to drop that non-default setting."""
    flags = ['--operator=' + getpass.getuser()] if action == 'up' else []
    result = subprocess.run(['tailscale', action, *flags], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('Tailscale could not ' + ('connect.' if action == 'up' else 'disconnect.'))


def next_step(action, state):
    """The terminal step an action needs first, or None when it can run here."""
    if not state.get('installed') or state.get('state') == 'unavailable':
        return 'setup'
    if action == 'connect' and state.get('state') == 'signed-out':
        return 'login'
    if state.get('operator') is not True:
        return action
    return None


def peer_name(address):
    state = tailscale_status.read()
    return next((peer['name'] for peer in state.get('peers', []) if peer['address'] == address), address)


def send_to(address):
    target = str(ipaddress.ip_address(address))
    from portal import choose_files
    files = [path.resolve(strict=True) for path in choose_files('Send with Taildrop to ' + peer_name(target))]
    if not files:
        return
    if any(not path.is_file() for path in files):
        raise ValueError('Taildrop sends files, not folders.')
    notify('Sending ' + (printable(files[0].name) if len(files) == 1 else f'{len(files)} files') + '…')
    result = subprocess.run(['tailscale', 'file', 'cp', '--', *map(str, files), target + ':'],
                            capture_output=True, text=True, timeout=SEND_TIMEOUT)
    if result.returncode:
        raise RuntimeError('Taildrop could not send the files. Check that the device is online and yours.')
    notify('Sent to ' + peer_name(target) + '.')


def background(arguments):
    """Panel actions: no terminal unless a step needs one; failures become notifications."""
    action = arguments[0]
    try:
        if action == 'open-folder':
            INBOX.mkdir(mode=0o700, parents=True, exist_ok=True)
            open_detached(['xdg-open', str(INBOX)])
        elif action == 'send-to' and len(arguments) == 2:
            send_to(arguments[1])
        elif action in ('connect', 'disconnect') and len(arguments) == 1:
            step = next_step(action, tailscale_status.read())
            if step:
                open_terminal(step)
            else:
                switch('up' if action == 'connect' else 'down')
        else:
            raise ValueError('Unknown action.')
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        notify(str(error) if isinstance(error, RuntimeError) else 'The Tailscale action failed.')
        raise SystemExit(1)


def send_from_terminal():
    answer = collect('Choose files', [Step('files', 'File paths',
                     description='Enter full paths separated by spaces; quote paths containing spaces.')])
    files = [Path(filename).expanduser().resolve(strict=True) for filename in shlex.split(answer['files'])]
    if not files or any(not filename.is_file() for filename in files):
        raise ValueError('Choose regular files.')
    status = json.loads(run(['tailscale', 'status', '--json']))
    if status.get('BackendState') != 'Running':
        raise RuntimeError('Connect Tailscale first.')
    destination = choose('Send to your online device', own_online_peers(status))
    run(['tailscale', 'file', 'cp', '--', *map(str, files), destination + ':'], timeout=SEND_TIMEOUT)
    print('Files sent.')
    wait_for_escape()


def ping(address):
    """Three pings that say whether the path to a device is direct or through a relay."""
    try:
        ipaddress.ip_address(address)
    except ValueError:
        raise RuntimeError('Choose a device from the Tailscale panel to ping.') from None
    subprocess.run(['tailscale', 'ping', '--c', '3', '--', address], check=False)
    wait_for_escape()


def receive():
    print(announce(fetch(wait=False, timeout=120)))
    print('Saved in ~/Documents/Taildrop.')
    wait_for_escape()


def main(action):
    if not shutil.which('tailscale') and action != 'setup':
        print('Tailscale is missing. Install it with Set up Tailscale.')
        wait_for_escape()
        return
    if action == 'setup':
        if not CORE_SETUP.is_file():
            raise RuntimeError("This Eitr version has no Remote Access setup; install the tailscale package and enable tailscaled.")
        subprocess.run([sys.executable, str(CORE_SETUP), 'away', 'setup'], check=True)
    elif action == 'operator':
        allow_operator()
    elif action == 'login':
        if tailscale_status.read().get('operator') is not True:
            allow_operator()
        login()
    elif action in ('connect', 'disconnect'):
        state = tailscale_status.read()
        if state.get('operator') is not True:
            allow_operator()
        if action == 'connect' and state.get('state') == 'signed-out':
            login()
        switch('up' if action == 'connect' else 'down')
    elif action == 'send':
        send_from_terminal()
    elif action == 'receive':
        receive()
    elif action == 'ping':
        ping(sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != '--terminal' else '')
    elif action == 'status':
        subprocess.run(['tailscale', 'status'], check=False)
        print()
        subprocess.run(['tailscale', 'netcheck'], check=False)
        wait_for_escape()
    elif action == 'undo-setup':
        if not CORE_SETUP.is_file():
            raise RuntimeError("This Eitr version has no Remote Access setup to undo.")
        subprocess.run([sys.executable, str(CORE_SETUP), 'away', 'undo'], check=True)
    else:
        raise ValueError('Unknown action.')


if __name__ == '__main__':
    if sys.argv[1:2] and sys.argv[1] in BACKGROUND and '--terminal' not in sys.argv:
        background(sys.argv[1:])
    else:
        launch(main)
