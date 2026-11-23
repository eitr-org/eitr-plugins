#!/usr/bin/env python3
"""One small snapshot. Bar refresh never fetches the installed model inventory."""
import json
import sys
import subprocess
import client


def text(value):
    return ''.join(character for character in str(value or '') if character.isprintable())[:160]


def models(payload, *, loaded=False):
    entries = payload.get('models', [])
    if not isinstance(entries, list):
        raise ValueError('Ollama returned an invalid model list.')
    if len(entries) > 100:
        raise ValueError('The model inventory exceeds this panel’s 100-model limit.')
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = text(entry.get('name') or entry.get('model'))
        size = entry.get('size', 0)
        size = max(0, size) if type(size) is int else 0
        item = {'name': name, 'size': size, 'modified': text(entry.get('modified_at'))}
        if loaded and type(entry.get('size_vram')) is int:
            item['vram'] = max(0, min(size, entry['size_vram']))
            item['ram'] = size - item['vram']
        result.append(item)
    return result


def read(*, bar=False):
    result = {'configured': client.configured(), 'ready': False, 'running': False, 'loaded': [], 'installed': [],
              'defaultModel': client.DEFAULT_MODEL, 'pull': client.read_state(), 'error': ''}
    try:
        if result['pull'].get('state') == 'downloading' and not client.active(client.PULL_UNIT):
            result['pull'] = {**result['pull'], 'state': 'interrupted'}
        if not result['configured']:
            return result
        result['running'] = client.active()
        if not bar:
            result['ready'] = client.ready()
            if not result['ready']:
                return result
        if not result['running']:
            return result
        result['loaded'] = models(client.request('ps'), loaded=True)
        if not bar:
            result['installed'] = models(client.request('tags'))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result['error'] = text(error)
    return result


def encode(snapshot):
    serialized = json.dumps(snapshot, ensure_ascii=False)
    if len(serialized.encode()) > 60 * 1024:
        serialized = json.dumps({**snapshot, 'loaded': [], 'installed': [],
                                 'error': 'The model inventory is too large for this panel.'}, ensure_ascii=False)
    return serialized


if __name__ == '__main__':
    if sys.argv[1:] not in (['--json'], ['--bar']):
        raise SystemExit('Usage: status.py --json|--bar')
    print(encode(read(bar=sys.argv[1:] == ['--bar'])))
