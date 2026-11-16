#!/usr/bin/env python3
"""JSON CLI used by the panel and its lightweight bar status command."""
import argparse
import fcntl
import json
import sys

import browser
import player
from storage import folder, read, write


def settings():
    saved = read(folder('CONFIG') / 'settings.json', {})
    if not isinstance(saved, dict):
        raise RuntimeError('Saved Radio Globe settings are invalid')
    favorites = saved.get('favorites', [])
    if not isinstance(favorites, list):
        raise RuntimeError('Saved Radio Globe favourites are invalid')
    return dict(favorites=[entry for record in favorites[:200] if (entry := browser.station(record))])


def state():
    saved = settings()
    playing = player.status()
    return dict(playing=playing, favorites=saved['favorites'])


def action(command, value=None):
    if command == 'status':
        return dict(playing=player.status())
    if command == 'state':
        return state()
    if command == 'countries':
        return browser.countries()
    with (folder('CONFIG') / 'settings.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        saved = settings()
        if command == 'play':
            player.play(value)
        elif command == 'stop':
            player.stop()
        elif command == 'favorite':
            entry = browser.station(value)
            if not entry:
                raise ValueError('Only checked HTTP or HTTPS stations can be saved')
            existing = any(record['stationuuid'] == entry['stationuuid'] for record in saved['favorites'])
            saved['favorites'] = [record for record in saved['favorites'] if record['stationuuid'] != entry['stationuuid']]
            if not existing:
                if len(saved['favorites']) >= 200:
                    raise ValueError('The favourites list is full (200 stations)')
                saved['favorites'].append(entry)
            write(folder('CONFIG') / 'settings.json', saved)
        else:
            raise ValueError('Unknown Radio Globe command')
        return state()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'state', 'countries', 'stations', 'play', 'stop', 'favorite'])
    parser.add_argument('values', nargs='*')
    args = parser.parse_args()
    # A hard outer deadline also bounds DNS, file locking and IPC.
    import signal
    signal.signal(signal.SIGALRM, browser.deadline)
    signal.alarm(9)
    try:
        if args.command == 'stations':
            if len(args.values) != 3:
                raise ValueError('Station search needs a mode, value and offset')
            result = browser.stations(args.values[0], args.values[1], int(args.values[2]))
        else:
            value = None
            if args.command in ('play', 'favorite'):
                payload = sys.stdin.read(8193)
                if len(payload) > 8192:
                    raise ValueError('Station data is too large')
                value = json.loads(payload)
            result = action(args.command, value)
        print(json.dumps(dict(ok=True, **result), ensure_ascii=False, separators=(',', ':')))
    except (OSError, RuntimeError, ValueError, TypeError) as error:
        print(json.dumps(dict(ok=False, error=str(error)), ensure_ascii=False))
        return 1
    finally:
        signal.alarm(0)
    return 0


if __name__ == '__main__':
    sys.exit(main())
