"""Render the real World clock components with an inert API in both palettes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required')
class WorldClockRenderTests(unittest.TestCase):
    def test_panel_and_bar_palettes_formats_and_empty_state(self):
        cities = [
            {'zone': 'Europe/Lisbon', 'label': 'LIS', 'time24': '14:05', 'time12': '2:05 PM', 'day': 'Today', 'offset': '+3 h'},
            {'zone': 'Asia/Tokyo', 'label': 'TYO', 'time24': '23:05', 'time12': '11:05 PM', 'day': 'Tomorrow', 'offset': '+12 h'},
            {'zone': 'America/New_York', 'label': 'NYC', 'time24': '09:05', 'time12': '9:05 AM', 'day': 'Today', 'offset': '-2 h'}
        ]
        with tempfile.TemporaryDirectory(prefix='eitr-world-render-') as directory:
            folder = Path(directory)
            for light in (False, True):
                capture_root = Path(os.environ.get('WORLD_CLOCK_RENDERS', directory))
                capture_root.mkdir(parents=True, exist_ok=True)
                captures = [str(capture_root / ('world-clock-' + kind + ('-light' if light else '-dark') + '.png')) for kind in ('panel', 'bar')]
                fixture = FIXTURE.replace('LIGHT', str(light).lower()).replace('PLUGIN', (ROOT / 'plugins/world-clock').as_uri())
                fixture = fixture.replace('STATUS', json.dumps({'cities': cities, 'barCount': 2, 'updated': 1, 'zones': ['Europe/Lisbon', 'Asia/Tokyo']})).replace('CAPTURES', json.dumps(captures))
                (folder / 'fixture.qml').write_text(fixture)
                environment = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                                   QML_IMPORT_PATH=str(ROOT.parent / 'eitr/quickshell'), HOME=directory,
                                   EITR_CODE_ROOT=str(ROOT.parent / 'eitr'), DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent',
                                   HYPRLAND_INSTANCE_SIGNATURE='', **{name: directory for name in (
                                       'XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_RUNTIME_DIR')})
                result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'fixture.qml')],
                                        env=environment, capture_output=True, text=True, timeout=10)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output)
                self.assertIn('WORLD_CLOCK_RENDER_OK', output)
                for error in ('ReferenceError', 'TypeError', 'Binding loop', 'Cannot anchor', 'Unable to assign', 'Error:'):
                    self.assertNotIn(error, output)
                self.assertTrue(all(Path(capture).is_file() for capture in captures))
                settings = json.loads((folder / 'eitr/plugins/world-clock.json').read_text())
                self.assertEqual(settings['barCount'], 1)
                self.assertEqual([city['label'] for city in settings['cities']], ['HOME', 'NYC', 'DEL'])


FIXTURE = r"""
import QtQuick
import Quickshell
ShellRoot {
    QtObject {
        id: api
        property color foreground: LIGHT ? "#252936" : "#e9eef1"
        property color background: LIGHT ? "#f5f0e7" : "#18212b"
        property color accent: "#70ba9a"
        property string fontFamily: "DejaVu Sans Mono"
        property int captionSize: 12
        property int bodySize: 13
        property int headingSize: 16
        property real radius: 4
        property string clockFormat: "24h"
        property string dataText: JSON.stringify(STATUS)
        property string streamLine: ""
        property string dataError: ""
        function runDataCommand() {}
    }
    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 440; implicitHeight: 560
        color: api.background
        Rectangle {
        id: canvas; anchors.fill: parent; color: api.background
        Loader {
            id: panel
            x: 20; y: 20; width: 400
            Component.onCompleted: setSource("PLUGIN/WorldClockPanel.qml", {api: api})
        }
        Rectangle {
            id: strip
            x: 20; y: 480; width: 400; height: 50
            color: api.background
            border.color: Qt.alpha(api.foreground, 0.15)
            Loader {
                id: bar
                anchors.centerIn: parent
                Component.onCompleted: setSource("PLUGIN/WorldClockBar.qml", {api: api})
            }
        }
        Timer {
            id: edits
            interval: 100; repeat: true
            property int stage: 0
            onTriggered: {
                const current = panel.item.status;
                if (stage === 0) { panel.item.changeCity(0, "down", ""); stage = 1; }
                else if (stage === 1 && current.cities[0].label === "TYO") { panel.item.changeCity(1, "label", "HOME"); stage = 2; }
                else if (stage === 2 && current.cities[1].label === "HOME") { panel.item.changeCity(0, "remove", ""); stage = 3; }
                else if (stage === 3 && current.cities.length === 2) {
                    panel.item.save({barCount: 1, cities: current.cities.map(city => ({zone: city.zone, label: city.label})).concat([{zone:"Asia/Kolkata", label:"DEL"}])});
                    stage = 4;
                } else if (stage === 4 && current.barCount === 1 && current.cities.length === 3 && current.cities[2].label === "DEL") {
                    console.log("WORLD_CLOCK_RENDER_OK"); Qt.quit();
                }
                if (panel.item.error) { console.error(panel.item.error); Qt.exit(1); }
            }
        }
        Timer {
            interval: 300; running: true
            onTriggered: {
                if (panel.status !== Loader.Ready || bar.status !== Loader.Ready || bar.item.implicitWidth <= 0) { console.error("Components not ready"); Qt.exit(1); return; }
                const original = api.dataText;
                api.dataText = JSON.stringify({cities: [], barCount:1, updated:2, zones:[]});
                if (bar.item.implicitWidth !== 0 || bar.item.implicitHeight !== 0) { console.error("Empty bar must be zero-sized"); Qt.exit(1); return; }
                api.dataText = original;
                api.clockFormat = "12h";
                Qt.callLater(() => {
                    canvas.grabToImage(result => {
                        result.saveToFile(CAPTURES[0]);
                        strip.grabToImage(image => { image.saveToFile(CAPTURES[1]); edits.start(); });
                    });
                });
            }
        }
        }
    }
}
"""
