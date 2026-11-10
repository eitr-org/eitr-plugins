#!/usr/bin/env python3
"""The plugin's user service: wait for Taildrop files and announce each arrival.

Taildrop only accepts files from devices signed in to the same account. While
Tailscale is missing, stopped or not yet allowed for this account, the loop waits
and retries with back-off instead of failing, so systemd never restarts it in a loop."""
import shutil
import subprocess
import time

from taildrop import announce, fetch

FIRST_RETRY = 5
LAST_RETRY = 300


def receive_forever(sleep=time.sleep, rounds=None):
    delay = FIRST_RETRY
    while rounds is None or rounds > 0:
        if rounds is not None:
            rounds -= 1
        if not shutil.which('tailscale'):
            sleep(LAST_RETRY)
            continue
        try:
            names = fetch(wait=True)
        except (OSError, RuntimeError, subprocess.SubprocessError):
            sleep(delay)
            delay = min(LAST_RETRY, delay * 2)
            continue
        delay = FIRST_RETRY
        if names:
            announce(names)
        else:
            sleep(FIRST_RETRY)


if __name__ == '__main__':
    receive_forever()
