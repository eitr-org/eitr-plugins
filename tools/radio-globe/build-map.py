#!/usr/bin/env python3
"""Import public-domain Natural Earth land and IANA representative locations."""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'plugins/radio-globe/data'


def angle(value, digits):
    sign = -1 if value[0] == '-' else 1
    degrees = int(value[1:digits + 1])
    minutes = int(value[digits + 1:digits + 3])
    seconds = int(value[digits + 3:] or '0')
    return round(sign * (degrees + minutes / 60 + seconds / 3600), 2)


def markers(source):
    """One point per country: the spherical mean of all its time zone locations.

    A country's first zone is often an outlying island (Brazil's is Fernando de Noronha), so
    averaging them all lands inside the country; averaging on the sphere keeps countries that
    span the date line (Kiribati, Fiji) in the Pacific."""
    sums = {}
    for line in source.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        country, coordinate, *_ = line.split('\t')
        split = next(index for index in range(1, len(coordinate)) if coordinate[index] in '+-')
        latitude = math.radians(angle(coordinate[:split], 2))
        longitude = math.radians(angle(coordinate[split:], 3))
        total = sums.setdefault(country, [0.0, 0.0, 0.0])
        total[0] += math.cos(latitude) * math.cos(longitude)
        total[1] += math.cos(latitude) * math.sin(longitude)
        total[2] += math.sin(latitude)
    result = {}
    for country, (x, y, z) in sums.items():
        result[country] = [round(math.degrees(math.atan2(z, math.hypot(x, y))), 2), round(math.degrees(math.atan2(y, x)), 2)]
    return result


def simplify(points, tolerance=0.4):
    if len(points) < 3:
        return points
    start, end = points[0], points[-1]
    delta_x, delta_y = end[0] - start[0], end[1] - start[1]
    length = delta_x ** 2 + delta_y ** 2
    distances = []
    for longitude, latitude in points[1:-1]:
        fraction = max(0, min(1, ((longitude - start[0]) * delta_x + (latitude - start[1]) * delta_y) / length)) if length else 0
        distances.append((longitude - start[0] - fraction * delta_x) ** 2 + (latitude - start[1] - fraction * delta_y) ** 2)
    maximum = max(distances)
    if maximum <= tolerance ** 2:
        return [start, end]
    pivot = distances.index(maximum) + 1
    return simplify(points[:pivot + 1], tolerance)[:-1] + simplify(points[pivot:], tolerance)


def land(source):
    result = []
    for feature in json.loads(source.read_text())['features']:
        geometry = feature['geometry']
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        for polygon in polygons:
            ring = simplify(polygon[0])
            if len(ring) >= 4:
                result.append([round(coordinate, 1) for point in ring for coordinate in point[:2]])
    return result


def validate(outlines):
    if not isinstance(outlines, list) or not outlines:
        raise ValueError('No land polygons')
    for ring in outlines:
        if len(ring) < 6 or len(ring) % 2:
            raise ValueError('Invalid land ring')
        if any(not -180 <= longitude <= 180 or not -90 <= latitude <= 90 for longitude, latitude in zip(ring[::2], ring[1::2])):
            raise ValueError('Land coordinate out of range')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--land', type=Path, help='Natural Earth ne_110m_land.geojson to import')
    parser.add_argument('--zone-tab', type=Path, default=Path('/usr/share/zoneinfo/zone.tab'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outlines = land(args.land) if args.land else json.loads((DATA / 'land.json').read_text())
    validate(outlines)
    locations = markers(args.zone_tab)
    if args.check:
        if json.loads((DATA / 'countries.json').read_text()) != locations:
            raise SystemExit('Bundled marker locations differ from this IANA zone.tab')
        print(f'{len(outlines)} land rings and {len(locations)} country markers validated')
    else:
        for filename, payload in [('land.json', outlines), ('countries.json', locations)]:
            (DATA / filename).write_text(json.dumps(payload, sort_keys=True, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
