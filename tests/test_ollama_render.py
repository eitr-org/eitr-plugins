"""Render real Eitr controls with an inert API; never connect to the desktop bus."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BAR = ROOT.parent / 'eitr/quickshell/desktop-bar'
spec = importlib.util.spec_from_file_location('ollama_layout_render', BAR / 'tests/layout_render.py')
rendering = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rendering)


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required for offscreen rendering')
class OllamaRenderTests(unittest.TestCase):
    def test_bar_publishes_live_details_without_a_second_tooltip(self):
        source = (ROOT / 'plugins/ollama/OllamaBarIcon.qml').read_text()
        for own_hover_type in ('PopupWindow', 'HoverHandler', 'Timer'):
            self.assertNotIn(own_hover_type, source)
        scenarios = [
            ({'loaded': [{'name': 'qwen3:4b'}], 'pull': {}}, 'qwen3:4b'),
            ({'loaded': [{'name': 'qwen3:4b'}, {'name': 'llama3.2:3b'}],
              'pull': {'state': 'downloading', 'model': 'gemma3:1b'}},
             'qwen3:4b, llama3.2:3b · Downloading · gemma3:1b'),
            ({'loaded': [], 'pull': {'state': 'downloading', 'model': 'gemma3:1b'}},
             'Downloading · gemma3:1b'),
            ({'loaded': [], 'pull': {'state': 'completed', 'model': 'gemma3:1b'}}, ''),
            ({'loaded': [], 'pull': {'state': 'failed', 'model': 'gemma3:1b'}}, ''),
            ({'loaded': [{'name': 'gemma3:1b'}], 'pull': {}}, 'gemma3:1b'),
            ({'loaded': [], 'pull': {}, 'running': False}, ''),
            (None, ''),
            ({'loaded': [{'name': 'qwen3:4b'}], 'pull': {}}, 'qwen3:4b'),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copytree(ROOT / 'plugins/ollama', folder / 'ollama')
            fixture = '''import QtQuick
import Quickshell
import "ollama" as Plugin
ShellRoot {
 id: root
 property int step: 0
 property var scenarios: SCENARIOS
 QtObject {
  id: api
  property color foreground: "#e6f1e9"
  property color background: "#10231c"
  property color accent: "#68aa87"
  property string detail: "stale"
  property string dataText: root.scenarios[root.step][0] === null ? "invalid JSON"
      : JSON.stringify(root.scenarios[root.step][0])
 }
 FloatingWindow {
  visible:true; implicitWidth:40; implicitHeight:40
  Plugin.OllamaBarIcon { id:icon; api:api }
 }
 Timer {
  interval:80; repeat:true; running:true
  onTriggered: {
   const expected = root.scenarios[root.step][1];
   if (api.detail !== expected || icon.Accessible.description !== expected) {
    console.error("DETAIL_MISMATCH", root.step, api.detail, expected);
    Qt.quit(); return;
   }
   if (root.step === root.scenarios.length - 1) {
    console.log("OLLAMA_DETAIL_OK"); Qt.quit(); return;
   }
   root.step++;
  }
 }
}
'''.replace('SCENARIOS', json.dumps(scenarios))
            path = folder / 'OllamaDetail.qml'
            path.write_text(fixture)
            status, log = rendering.render(path, rendering.render_environment(folder), 10)
            self.assertEqual(status, 0, log)
            self.assertIn('OLLAMA_DETAIL_OK', log)
            for problem in ('DETAIL_MISMATCH', 'QML error', 'ReferenceError', 'TypeError', 'Binding loop'):
                self.assertNotIn(problem, log)

    def test_panel_and_bar_in_both_themes(self):
        output = Path(os.environ.get('EITR_OLLAMA_RENDERS', ROOT.parent))
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            rendering.copy_runtime(folder / 'runtime')
            shutil.copytree(ROOT / 'plugins/ollama', folder / 'ollama')
            fixture = '''import QtQuick
import Quickshell
import "runtime" as Bar
import "ollama" as Plugin
ShellRoot {
 id: root
 property int step: 0
 property bool light: step % 2 === 1
 property color foreground: light ? "#203b30" : "#e6f1e9"
 property color background: light ? "#f3f8f1" : "#10231c"
 property color accent: light ? "#32644c" : "#68aa87"
 property var sample: ({configured:step!==3,ready:step!==3,running:step!==2 && step!==3,defaultModel:"qwen3:4b",error:step===5 ? "offline" : "",
  loaded:step>=2 ? [] : [{name:"qwen3:4b",size:3200000000,vram:2400000000,ram:800000000}],
  installed:step===5 ? [] : [{name:"qwen3:4b",size:2500000000,modified:"2026-11-15T12:00:00Z"},
   {name:"llama3.2:3b",size:2000000000,modified:"2026-11-14T12:00:00Z"}],
  pull:step>=2 ? ({}) : {state:"downloading",model:"gemma3:1b",total:806000000,completed:350000000}})
 QtObject {
  id: api
  property color foreground: root.foreground
  property color background: root.background
  property color accent: root.accent
  property var palette: ({color0:background,color7:foreground,color4:accent})
  property string fontFamily: Bar.DesktopFonts.family
  property int headingSize: 16
  property int bodySize: 13
  property int captionSize: 12
  property int barTextSize: 14
  property int radius: 8
  property bool observed: true
  property string detail: ""
  property string dataText: JSON.stringify(root.sample)
  property string dataError: ""
  property var controls: ({button:button,textField:field,dropdown:dropdown})
  function runDataCommand() {}
 }
 Component { id: button; Bar.PanelButton { foreground:api.foreground; text:"" } }
 Component { id: field; Bar.PanelTextField { foreground:api.foreground; accent:api.accent } }
 Component { id: dropdown; Bar.ChoiceDropdown { foreground:api.foreground; background:api.background; gold:api.accent } }
 FloatingWindow {
  visible:true; implicitWidth:460; implicitHeight:1100; color:root.background
  Rectangle {
   id: canvas
   width:450; height:panel.implicitHeight+100
   color:root.background
   Plugin.OllamaBarIcon { id: icon; x:22; y:18; width:24; height:24; api:api }
   Text { x:58; y:21; width:370; wrapMode:Text.Wrap; textFormat:Text.PlainText
    text:"Ollama" + (api.detail ? " · " + api.detail : ""); color:api.foreground; font.pixelSize:13 }
   Plugin.OllamaPanel { id:panel; x:20; y:68; width:410; height:implicitHeight; api:api; pendingDelete:root.step===4 ? "qwen3:4b" : "" }
  }
 }
 Timer {
  interval:700; repeat:true; running:true
  onTriggered: {
   if (root.step > 5) return;
   canvas.grabToImage(function(result) {
    if (!result.saveToFile(OUTPUT + "/ollama-panel-" + ["dark", "light", "stopped", "setup", "delete", "error"][root.step] + ".png")) throw new Error("Panel capture failed");
    if (root.step >= 2) {
     if (root.step === 5) { console.log("OLLAMA_RENDER_OK"); Qt.quit(); }
     root.step++; return;
    }
    icon.grabToImage(function(iconResult) {
     if (!iconResult.saveToFile(OUTPUT + "/ollama-bar-" + (root.light ? "light" : "dark") + ".png")) throw new Error("Bar capture failed");
     root.step++;
    });
   });
  }
 }
}
'''.replace('OUTPUT', json.dumps(str(output)))
            path = folder / 'OllamaRender.qml'
            path.write_text(fixture)
            status, log = rendering.render(path, rendering.render_environment(folder), 20)
            self.assertEqual(status, 0, log)
            self.assertIn('OLLAMA_RENDER_OK', log)
            for problem in ('QML error', 'ReferenceError', 'TypeError', 'Binding loop', 'Could not create'):
                self.assertNotIn(problem, log)
            from PIL import Image
            for theme in ('dark', 'light'):
                for kind in ('panel', 'bar'):
                    with Image.open(output / ('ollama-' + kind + '-' + theme + '.png')) as capture:
                        self.assertGreater(len(capture.convert('RGB').getcolors(capture.width * capture.height)), 4)
