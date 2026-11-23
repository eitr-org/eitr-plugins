#!/usr/bin/env python3
"""Explicit argv only; setup and chat keep Eitr's existing entry points."""
import json
from pathlib import Path
import subprocess
import sys
import client


def run(arguments):
    if not arguments:
        raise ValueError('Missing action.')
    action, *values = arguments
    if action in ('setup', 'chat') and not values:
        command = ([str(client.CODE / 'walker/bin/walker'), '--provider', 'menus:ai-default']
                   if action == 'setup' else
                   ['python3', str(client.CODE / 'walker/scripts/actions/ai-assistant.py'), 'open'])
        subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if action == 'cancel' and not values:
        result = client.systemctl('stop', client.PULL_UNIT, timeout=7)
    elif action in ('start', 'stop') and not values:
        if not client.configured():
            raise ValueError('Open Eitr’s Default Assistant setup first.')
        if action == 'stop' and client.active(client.PULL_UNIT):
            raise ValueError('Cancel the download before stopping the service.')
        result = client.systemctl(action, '--no-block', client.UNIT)
    elif action == 'pull' and len(values) == 1:
        model = client.model_name(values[0])
        if not client.configured() or not client.active():
            raise ValueError('Start Eitr’s Ollama service first.')
        result = subprocess.run(['systemd-run', '--user', '--collect', '--quiet',
                                 '--unit=' + client.PULL_UNIT, '--property=RuntimeMaxSec=86400',
                                 '--property=TimeoutStopSec=5', sys.executable,
                                 str(Path(__file__).with_name('pull.py')), model],
                                capture_output=True, text=True, timeout=3, check=False)
    elif action in ('unload', 'delete-confirmed') and len(values) == 1:
        model = client.model_name(values[0])
        if not client.configured() or not client.active():
            raise ValueError('Start Eitr’s Ollama service first.')
        if action == 'delete-confirmed' and client.active(client.PULL_UNIT):
            raise ValueError('Cancel the download before deleting a model.')
        client.request('delete', {'model': model}, method='DELETE') if action == 'delete-confirmed' else \
            client.request('generate', {'model': model, 'keep_alive': 0, 'stream': False})
        return
    else:
        raise ValueError('Unsupported action or arguments.')
    if result.returncode:
        raise ValueError('The service action failed. Check the user service; a download may already be running.')


if __name__ == '__main__':
    try:
        run(sys.argv[1:])
        print(json.dumps({'ok': True}))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        raise SystemExit(1)
