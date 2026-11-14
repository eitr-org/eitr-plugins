#!/usr/bin/env python3
"""Offline IANA clocks and atomic, plugin-owned preferences."""
import argparse
from datetime import datetime, timezone
import fcntl
from functools import lru_cache
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from zoneinfo import ZoneInfo, available_timezones

MAX_CITIES = 24


@lru_cache(maxsize=1)
def zones():
    return available_timezones()


def settings_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'eitr/plugins/world-clock.json'


def validate(settings):
    if not isinstance(settings, dict) or set(settings) != {'cities', 'barCount'}:
        raise ValueError('Invalid world clock settings')
    if type(settings['barCount']) is not int or settings['barCount'] not in (1, 2):
        raise ValueError('Choose one or two bar cities')
    cities = settings['cities']
    if not isinstance(cities, list) or len(cities) > MAX_CITIES:
        raise ValueError('Choose at most 24 cities')
    seen = set()
    for city in cities:
        if not isinstance(city, dict) or set(city) != {'zone', 'label'}:
            raise ValueError('Invalid city')
        zone, label = city['zone'], city['label']
        if not isinstance(zone, str) or zone not in zones() or zone in seen:
            raise ValueError('Choose a unique IANA time zone')
        if not isinstance(label, str) or not label.strip() or len(label) > 12 or any(not character.isprintable() for character in label):
            raise ValueError('Labels must contain 1–12 printable characters')
        seen.add(zone)
    return settings


def read_settings():
    try:
        return validate(json.loads(settings_path().read_text()))
    except FileNotFoundError:
        return {'cities': [], 'barCount': 1}


def save_settings(settings):
    validate(settings)
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, filename = tempfile.mkstemp(prefix='.world-clock-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as output:
            json.dump(settings, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(filename, path)
    finally:
        Path(filename).unlink(missing_ok=True)


def clock_rows(settings, now=None, local_zone=None):
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(local_zone)
    rows = []
    for city in settings['cities']:
        there = now.astimezone(ZoneInfo(city['zone']))
        minutes = round((there.utcoffset() - local.utcoffset()).total_seconds() / 60)
        hours, remainder = divmod(abs(minutes), 60)
        offset = ('+' if minutes >= 0 else '-') + str(hours) + ' h'
        if remainder:
            offset += ' ' + str(remainder).zfill(2)
        day = (there.date() - local.date()).days
        rows.append({**city, 'time24': there.strftime('%H:%M'),
                     'time12': there.strftime('%I:%M %p').lstrip('0'),
                     'day': 'Yesterday' if day < 0 else 'Tomorrow' if day > 0 else 'Today',
                     'offset': offset})
    return rows


def snapshot():
    try:
        settings = read_settings()
    except (OSError, ValueError, TypeError, KeyError):
        return {'cities': [], 'barCount': 1, 'zones': [], 'updated': time.time(),
                'error': 'Could not read World clock preferences. Correct the plugin settings file and reopen this panel.'}
    return {**settings, 'cities': clock_rows(settings), 'updated': time.time(),
            'zones': sorted(zones())}


def stream_snapshot():
    data = snapshot()
    data.pop('zones', None)
    data['cities'] = [[city[key] for key in ('zone', 'label', 'time24', 'time12', 'day', 'offset')]
                      for city in data['cities']]
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def minute_delay(timestamp):
    return 60 - timestamp % 60


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'stream', 'save'))
    parser.add_argument('settings', nargs='?')
    arguments = parser.parse_args()
    if arguments.action == 'save':
        settings = validate(json.loads(arguments.settings))
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.with_suffix('.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            save_settings(settings)
    if arguments.action == 'stream':
        while True:
            print(stream_snapshot(), flush=True)
            time.sleep(minute_delay(time.time()))
    else:
        print(json.dumps(snapshot(), ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
