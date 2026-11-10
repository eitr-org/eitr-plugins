"""Move waiting Taildrop files into ~/Documents/Taildrop and name what arrived."""
import html
from pathlib import Path
import subprocess

INBOX = Path.home() / 'Documents/Taildrop'


def printable(name):
    return ''.join(character if character.isprintable() else '?' for character in name)


def snapshot(folder):
    return {entry.name: (entry.stat().st_mtime_ns, entry.stat().st_size) for entry in folder.iterdir() if entry.is_file()}


def fetch(*, wait, timeout=None, inbox=None):
    """Run `tailscale file get`; returns the names added or changed. Name conflicts get a
    numbered name, so nothing already in the folder is overwritten."""
    inbox = inbox or INBOX
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    before = snapshot(inbox)
    arguments = ['tailscale', 'file', 'get', '--conflict=rename', *(['--wait'] if wait else []), str(inbox)]
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError('Taildrop could not receive files. If permission is denied, allow this account to control Tailscale.')
    return sorted(name for name, stamp in snapshot(inbox).items() if before.get(name) != stamp)


def announce(names):
    message = ', '.join(printable(name) for name in names) if names else 'No waiting files.'
    subprocess.run(['notify-send', '--app-name=Taildrop', '--icon=folder-download', '--', 'Taildrop',
                    html.escape(message) + ('\nSaved in Documents/Taildrop' if names else '')],
                   check=False, timeout=10)
    return message
