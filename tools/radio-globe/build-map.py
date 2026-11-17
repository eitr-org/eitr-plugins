#!/usr/bin/env python3
"""Import public-domain Natural Earth land and country label points, with IANA zone fallbacks."""
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


def zone_markers(source):
    """Fallback points: the spherical mean of each country's time zone locations.

    Zones sit in cities, so this leans towards them (Australia's lands near Sydney); it is
    used only for the small territories Natural Earth's country file does not list."""
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


def ring_area(geometry):
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    return sum(abs(sum(ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
                       for index in range(len(ring) - 1))) / 2 for ring in (polygon[0] for polygon in polygons))


def label_markers(source):
    """Natural Earth's label point for each country: a spot chosen to sit well inside it.

    Several features can share a code (Australia and its Ashmore and Cartier Islands); the
    one with the most land wins."""
    best = {}
    for feature in json.loads(source.read_text())['features']:
        properties = feature['properties']
        code = properties.get('ISO_A2')
        if code in (None, '-99'):
            code = properties.get('ISO_A2_EH')
        if not code or code == '-99':
            continue
        area = ring_area(feature['geometry'])
        if code not in best or area > best[code][0]:
            best[code] = (area, [round(properties['LABEL_Y'], 2), round(properties['LABEL_X'], 2)])
    return {code: point for code, (_, point) in best.items()}


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


def land(source, tolerance=0.4):
    result = []
    for feature in json.loads(source.read_text())['features']:
        geometry = feature['geometry']
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        for polygon in polygons:
            ring = simplify(polygon[0], tolerance)
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
    parser.add_argument('--land-detail', type=Path, help='Natural Earth ne_50m_land.geojson for the zoomed-in outline')
    parser.add_argument('--countries', type=Path, help='Natural Earth ne_50m_admin_0_countries.geojson to import')
    parser.add_argument('--zone-tab', type=Path, default=Path('/usr/share/zoneinfo/zone.tab'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outlines = land(args.land) if args.land else json.loads((DATA / 'land.json').read_text())
    validate(outlines)
    # Zoomed in, the globe draws this finer outline: 1:50m, simplified to 0.1 degrees.
    detail = land(args.land_detail, 0.1) if args.land_detail else json.loads((DATA / 'land-detail.json').read_text())
    validate(detail)
    zones = zone_markers(args.zone_tab)
    if args.countries:
        locations = dict(zones, **label_markers(args.countries))
    else:
        locations = json.loads((DATA / 'countries.json').read_text())
    missing = sorted(set(zones) - set(locations))
    if missing:
        raise SystemExit('Countries without a marker: ' + ', '.join(missing))
    if any(not -90 <= latitude <= 90 or not -180 <= longitude <= 180 for latitude, longitude in locations.values()):
        raise SystemExit('Marker coordinate out of range')
    if args.check:
        print(f'{len(outlines)} land rings, {len(detail)} detailed rings and {len(locations)} country markers validated')
    else:
        for filename, payload in [('land.json', outlines), ('land-detail.json', detail), ('countries.json', locations)]:
            (DATA / filename).write_text(json.dumps(payload, sort_keys=True, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
