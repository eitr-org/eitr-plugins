"""Render plugin QML with real Eitr controls and inert data, outside the live session."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BAR = ROOT.parent / 'eitr/quickshell/desktop-bar'
sys.path.insert(0, str(BAR / 'tests'))
from layout_render import copy_runtime, render_environment


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required for offscreen renders')
class PhoneRenderTests(unittest.TestCase):
    def test_panel_bar_and_setup_in_both_themes(self):
        output = Path(os.environ.get('PHONE_LINK_RENDERS', '/tmp/phone-link-renders'))
        output.mkdir(parents=True, exist_ok=True)
        plugins = ['kdeconnect_share', 'kdeconnect_sftp', 'kdeconnect_findmyphone', 'kdeconnect_ping']
        devices = [dict(id=identifier, name=name, type=kind, battery=battery, paired=paired,
                        reachable=reachable, charging=charging, incoming=incoming, outgoing=False,
                        verification='123456' if incoming else '', plugins=plugins if paired and reachable else [])
                   for identifier, name, kind, battery, paired, reachable, charging, incoming in [
                       ('phone', 'Phone', 'phone', 80, True, True, True, False),
                       ('request', 'New phone', 'phone', None, False, True, False, True),
                       ('tablet', 'Tablet', 'tablet', None, True, False, False, False),
                       ('iphone', 'iPhone', 'phone', None, False, True, False, False)]]
        sample = json.dumps(dict(state='ready', devices=devices, total=len(devices)))
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            copy_runtime(folder)
            shutil.copytree(ROOT / 'plugins/phone-link', folder / 'phone')
            # The fixture displays inert data and never invokes a plugin action.
            fixture = '''import QtQuick
import Quickshell
import "." as Bar
import "phone" as Phone
ShellRoot {
 id: root
 property bool light: false
 property int phase: 0
 property var sample: SAMPLE
 property var stopped: ({state:"stopped",devices:[],total:0})
 QtObject {
  id: fake
  property color foreground: root.light ? "#203b30" : "#e6f1e9"
  property color background: root.light ? "#f3f8f1" : "#10231c"
  property color accent: root.light ? "#32644c" : "#68aa87"
  property var palette: ({foreground:foreground,background:background,accent:accent})
  property string fontFamily: "JetBrainsMono Nerd Font"
  property int bodySize: 13
  property int headingSize: 16
  property int captionSize: 12
  property int radius: 4
  property string detail: ""
  property string streamLine: JSON.stringify(root.phase === 1 ? root.stopped : root.sample)
  property string dataText: streamLine
  property string dataError: ""
  property bool observed: true
  property var controls: ({button:button})
  signal streamReceived(string line)
  function runDataCommand() {}
 }
 Component { id: button; Bar.PanelButton { foreground: fake.foreground; text: "" } }
 FloatingWindow {
  implicitWidth: 440; implicitHeight: 1000; visible: true; color: fake.background
  Rectangle {
   id: canvas
   color: fake.background; width: 400; height: page.implicitHeight + 100
   Phone.PhonePanel { id: page; api: fake; x: 18; y: 70; width: 364 }
   Rectangle {
    id: icons
    x: 18; y: 18; width: 128; height: 36; color: fake.background
    Phone.PhoneBarIcon { id: connected; api: fake; x: 12; y: 6 }
    Phone.PhoneBarIcon {
     api: QtObject {
      property color foreground: fake.foreground
      property color background: fake.background
      property string fontFamily: fake.fontFamily
      property int radius: 4
      property string streamLine: JSON.stringify(root.stopped)
      property string dataText: streamLine
      property string detail: ""
      signal streamReceived(string line)
     }
     x: 80; y: 6
    }
   }
  }
 }
 function expand(item) {
  if (item.device !== undefined && item.device.id === "phone") {
   const toggle = item.children[0].children.find(child => child.text === "Actions" && child.clicked !== undefined);
   if (!toggle) throw new Error("Missing Actions button");
   toggle.clicked();
   if (!item.expanded || toggle.text !== "Hide actions") throw new Error("Actions did not expand");
   item.confirming = true;
   toggle.clicked();
   if (item.expanded || item.confirming || toggle.text !== "Actions") throw new Error("Actions did not collapse");
   toggle.clicked();
  }
  for (const child of item.children || []) expand(child);
 }
 function checkDetail() {
  const expected = root.phase === 0 ? "Phone · 80%" : "No phone connected";
  if (fake.detail !== expected) throw new Error("Bad host detail: " + fake.detail);
  if (root.phase !== 0) return;
  const unknownBattery = JSON.parse(JSON.stringify(root.sample));
  unknownBattery.devices[0].battery = null;
  connected.update(JSON.stringify(unknownBattery));
  if (fake.detail !== "Phone") throw new Error("Unknown battery detail");
  connected.update("invalid");
  if (fake.detail !== "Phone") throw new Error("Invalid status replaced detail");
  connected.update(JSON.stringify(root.stopped));
  if (fake.detail !== "No phone connected") throw new Error("Disconnected detail");
  connected.update(JSON.stringify(root.sample));
  if (fake.detail !== expected) throw new Error("Reconnected detail");
 }
 Timer {
  interval: 500; running: true; repeat: true
  property bool saving: false
  onTriggered: {
   if (saving) return;
   root.expand(page);
   root.checkDetail();
   const theme = root.light ? "light" : "dark";
   saving = true;
   canvas.grabToImage(function(capture) {
    if (!capture.saveToFile("OUTPUT/" + (root.phase === 0 ? "panel-" : "setup-") + theme + ".png")) throw new Error("save failed");
    icons.grabToImage(function(bar) {
     if (root.phase === 0 && !bar.saveToFile("OUTPUT/bar-" + theme + ".png")) throw new Error("save failed");
     if (root.phase === 1 && root.light) { console.log("PHONE_RENDER_OK"); Qt.quit(); }
     if (root.phase === 1) { root.phase = 0; root.light = true; }
     else root.phase = 1;
     saving = false;
    });
   });
  }
 }
}
'''.replace('SAMPLE', sample).replace('OUTPUT', str(output))
            (folder / 'PhoneRender.qml').write_text(fixture)
            environment = render_environment(folder)
            environment['LANG'] = 'en_US.UTF-8'
            result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'PhoneRender.qml')],
                                    env=environment, text=True, capture_output=True, timeout=25)
            log = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, log)
            self.assertIn('PHONE_RENDER_OK', log)
            for warning in ('ReferenceError', 'TypeError', 'is not a type', 'Failed to load', 'Error:', 'Unable to assign'):
                self.assertNotIn(warning, log)
        from PIL import Image
        for theme in ('dark', 'light'):
            with Image.open(output / ('panel-' + theme + '.png')) as panel:
                self.assertEqual(panel.width, 400)
                self.assertGreater(panel.height, 400)
                self.assertGreater(len(panel.getcolors(panel.width * panel.height)), 10)


if __name__ == '__main__':
    unittest.main()
