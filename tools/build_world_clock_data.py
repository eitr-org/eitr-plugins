#!/usr/bin/env python3
"""Build the offline GeoNames catalog from an existing local download."""
import argparse
import gzip
import json
from pathlib import Path
from zoneinfo import available_timezones


def build(source, valid_zones=None):
    valid_zones = available_timezones() if valid_zones is None else valid_zones
    countries = {}
    for line in (source / 'countryInfo.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            fields = line.split('\t')
            countries[fields[0]] = fields[4]
    admins = {}
    for line in (source / 'admin1CodesASCII.txt').read_text().splitlines():
        fields = line.split('\t')
        admins[fields[0]] = fields[1]
    rows = []
    for line in (source / 'cities15000.txt').read_text().splitlines():
        fields = line.split('\t')
        if fields[17] in valid_zones:
            rows.append([fields[1], fields[2], admins.get(fields[8] + '.' + fields[10], ''),
                         fields[8], fields[17], int(fields[14])])
    rows.sort(key=lambda city: (-city[5], city[0], city[4]))
    return {'countries': countries, 'cities': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    arguments = parser.parse_args()
    payload = json.dumps(build(arguments.source), ensure_ascii=False, separators=(',', ':')).encode()
    arguments.output.write_bytes(gzip.compress(payload, mtime=0))


if __name__ == '__main__':
    main()
