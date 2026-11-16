#!/usr/bin/env python3
"""Render production QML and host controls with isolated settings and fake data."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BAR = ROOT.parent / 'eitr/quickshell/desktop-bar'
FIXTURE = ROOT / 'tools/radio-globe/fixture.qml.in'


def prepare(folder, light, scenario, output):
    controls = folder / 'components'
    controls.mkdir()
    for name in ('PanelButton', 'PanelTextField', 'ChoiceDropdown', 'SpinningGlyph', 'ChoiceEntryContent', 'ChoiceListSurface', 'OutlinedFrame'):
        shutil.copy(BAR / 'components' / (name + '.qml'), controls / (name + '.qml'))
    shutil.copy(BAR / 'PanelStyle.js', folder / 'PanelStyle.js')
    (folder / 'qmldir').write_text('singleton DesktopStyle DesktopStyle.qml\nsingleton DesktopFonts DesktopFonts.qml\n')
    (folder / 'DesktopStyle.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { property bool reduceMotion: true; function radius(value) { return value; } function motionDuration(value) { return 0; } }')
    (folder / 'DesktopFonts.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { property string family: "JetBrainsMono Nerd Font" }')
    eitr = folder / 'Eitr'
    eitr.mkdir()
    (eitr / 'qmldir').write_text('module Eitr\nsingleton I18n I18n.qml\nsingleton Paths Paths.qml\n')
    (eitr / 'I18n.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { function tr(value) { return value; } }')
    (eitr / 'Paths.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { function config(value) { return ' + json.dumps(str(folder)) + ' + "/" + value; } }')
    shutil.copytree(ROOT / 'plugins/radio-globe', folder / 'plugin')
    (folder / 'plugin/runtime.py').write_text('''import json, sys, time
from pathlib import Path
command = sys.argv[1]
with Path(__file__).with_name('calls.jsonl').open('a') as output:
    output.write(json.dumps({'arguments': sys.argv[1:], 'started': time.time()}) + '\\n')
data = json.loads(Path(__file__).with_name('fixture.json').read_text())
if command == 'countries': result = {'countries': data['countries'], 'stale': False}
elif command == 'stations':
    if sys.argv[3] == 'slow': time.sleep(0.2)
    if sys.argv[3] == 'failure':
        print(json.dumps({'ok': False, 'error': 'Radio Browser is unavailable. Check your connection and retry.'}))
        sys.exit(0)
    result = {'stations': data['stations'], 'more': False}
else: result = data['state']
print(json.dumps({'ok': True, **result}))
''')
    station = dict(stationuuid='fixture', name='Rádio Aurora', tags='ambient, jazz, instrumental',
                   codec='MP3', bitrate=128, countrycode='BR', url='https://stream.example/live', lastcheckok=1)
    countries = [dict(code=code, name=name, count=count, location=location) for code, name, count, location in
                 [('BR', 'Brazil', 2500, [-15, -48]), ('US', 'United States', 9000, [39, -98]),
                  ('CA', 'Canada', 1100, [55, -106]), ('AR', 'Argentina', 900, [-35, -65]),
                  ('GB', 'United Kingdom', 2000, [54, -2]), ('FR', 'France', 1800, [47, 2]),
                  ('DE', 'Germany', 2500, [51, 10]), ('ES', 'Spain', 1200, [40, -4]),
                  ('ZA', 'South Africa', 300, [-29, 24]), ('NG', 'Nigeria', 200, [9, 8]),
                  ('JP', 'Japan', 500, [36, 138]), ('AU', 'Australia', 800, [-25, 134])]]
    stations = [station, {**station, 'stationuuid': 'second', 'name': 'World Jazz · São Paulo', 'tags': 'jazz, soul', 'codec': 'AAC', 'bitrate': 192},
                {**station, 'stationuuid': 'third', 'name': '<Live> Música sem fronteiras', 'tags': 'world, brasil', 'codec': 'OGG', 'bitrate': 96}]
    (folder / 'plugin/fixture.json').write_text(json.dumps(dict(countries=countries, stations=stations,
         state=dict(playing=dict(station=station), favorites=[station]))))
    settings = folder / 'quickshell/desktop-bar'
    settings.mkdir(parents=True)
    (settings / 'bar-settings.json').write_text('{"reduceMotion":"yes"}')
    fixture = FIXTURE.read_text().replace('LIGHT', str(light).lower()).replace('SCENARIO', json.dumps(scenario)).replace('OUTPUT', json.dumps(str(output)))
    (folder / 'fixture.qml').write_text(fixture)


def render(output, scenario='stations', light=False, locale='en_US'):
    with tempfile.TemporaryDirectory(prefix='radio-globe-render-') as temporary:
        folder = Path(temporary)
        prepare(folder, light, scenario, output)
        environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                           QML_IMPORT_PATH=str(folder), DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent',
                           HYPRLAND_INSTANCE_SIGNATURE='', HOME=temporary,
                           LANG=locale + '.UTF-8', LC_ALL=locale + '.UTF-8',
                           **{name: temporary for name in ('XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_RUNTIME_DIR', 'XDG_STATE_HOME', 'XDG_DATA_HOME')})
        result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'fixture.qml')],
                                env=environment, text=True, capture_output=True, timeout=15)
        log = result.stdout + result.stderr
        failures = ('ReferenceError', 'TypeError', 'Binding loop', 'Cannot anchor', 'Unable to assign', 'Error:', 'not available')
        if result.returncode or 'RADIO_RENDER_OK' not in log or any(failure in log for failure in failures):
            raise RuntimeError(log)
        if scenario == 'lifecycle':
            commands = [json.loads(line) for line in (folder / 'plugin/calls.jsonl').read_text().splitlines()]
            closed = float(re.search(r'RADIO_PANEL_CLOSED (\d+(?:\.\d+)?)', log)[1])
            if any(command['arguments'] == ['state'] and command['started'] > closed for command in commands):
                raise RuntimeError('State polling continued while the panel was closed')
        return log


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent)
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    for theme in ('dark', 'light'):
        for scenario in ('stations', 'offline', 'favorites', 'compact'):
            capture = arguments.output / ('radio-globe-' + scenario + '-' + theme + '.png')
            render(capture, scenario, light=theme == 'light')
            print(capture.name + ': RADIO_RENDER_OK')
