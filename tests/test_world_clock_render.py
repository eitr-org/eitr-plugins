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
            {'zone': 'Europe/Lisbon', 'label': 'LIS', 'name': 'Lisbon', 'country': 'PT', 'flag': '🇵🇹', 'time24': '14:05', 'time12': '2:05 PM', 'day': 'Today', 'offset': '+3 h'},
            {'zone': 'Asia/Tokyo', 'label': 'TYO', 'name': 'Tokyo', 'country': 'JP', 'flag': '🇯🇵', 'time24': '23:05', 'time12': '11:05 PM', 'day': 'Tomorrow', 'offset': '+12 h'},
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
                self.assertEqual(settings['cities'][0]['name'], 'Lisbon')
                self.assertEqual(settings['cities'][0]['country'], 'PT')
                self.assertEqual(settings['cities'][-1]['name'], 'Tokyo')
                self.assertEqual(settings['cities'][-1]['country'], 'JP')
                self.assertEqual([city['label'] for city in settings['cities']], ['HOME', 'NYC', 'DEL', 'TOK'])


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
        implicitWidth: 440; implicitHeight: 820
        color: api.background
        Rectangle {
        id: canvas; anchors.fill: parent; color: api.background
        Loader {
            id: panel
            x: 20; y: 20; width: 400; height: 700; clip: true
            Component.onCompleted: setSource("PLUGIN/WorldClockPanel.qml", {api: api})
            onLoaded: item.searchText = "california"
        }
        Rectangle {
            id: strip
            x: 20; y: 750; width: 400; height: 50
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
            property int stage: -2
            function findControl(item) {
                if (item.objectName === "barCountDropdown") return item;
                for (const child of item.children || []) {
                    const found = findControl(child);
                    if (found) return found;
                }
                return null;
            }
            onTriggered: {
                const current = panel.item.status;
                if (stage === -2) {
                    const dropdown = findControl(panel.item);
                    if (!dropdown || dropdown.count !== 10) { console.error("Missing 1–10 dropdown"); Qt.exit(1); return; }
                    dropdown.popup.open();
                    dropdown.currentIndex = 9;
                    dropdown.activated(9);
                    dropdown.popup.close();
                    stage = -1;
                } else if (stage === -1 && current.barCount === 10) { stage = 0; }
                else if (stage === 0) { panel.item.changeCity(0, "down", ""); stage = 1; }
                else if (stage === 1 && current.cities[0].label === "TYO") { panel.item.changeCity(1, "label", "HOME"); stage = 2; }
                else if (stage === 2 && current.cities[1].label === "HOME") { panel.item.changeCity(0, "remove", ""); stage = 3; }
                else if (stage === 3 && current.cities.length === 2) {
                    panel.item.save({barCount: 1, cities: current.cities.map(city => (city.name ? {zone: city.zone, label: city.label, name:city.name, country:city.country} : {zone:city.zone, label:city.label})).concat([{zone:"Asia/Kolkata", label:"DEL"}])});
                    stage = 4;
                } else if (stage === 4 && current.barCount === 1 && current.cities.length === 3 && current.cities[2].label === "DEL") {
                    panel.item.addCity({zone:"Asia/Tokyo", label:"TOK", name:"Tokyo", country:"JP"});
                    stage = 5;
                } else if (stage === 5 && current.cities.length === 4 && current.cities[3].country === "JP") {
                    console.log("WORLD_CLOCK_RENDER_OK"); Qt.quit();
                }
                if (panel.item.error) { console.error(panel.item.error); Qt.exit(1); }
            }
        }
        Timer {
            id: captureTimer
            interval: 100; running: true; repeat: true
            onTriggered: {
                if (panel.status !== Loader.Ready || bar.status !== Loader.Ready || bar.item.implicitWidth <= 0) { console.error("Components not ready"); Qt.exit(1); return; }
                if (panel.item.matches.length !== 30) return;
                captureTimer.stop();
                const original = api.dataText;
                api.dataText = JSON.stringify({cities: [], barCount:1, updated:2, zones:[]});
                if (bar.item.implicitWidth !== 24 || !bar.item.empty) { console.error("Empty bar must show the globe"); Qt.exit(1); return; }
                api.dataText = original;
                api.clockFormat = "12h";
                api.clockFormat = "24h";
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
