"""Offscreen Quickshell screenshot renderer for Notes and Hardware desktop widgets."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NOTES_QML = ROOT / 'plugins/notes/Notes.qml'
HARDWARE_QML = ROOT / 'plugins/hardware/Hardware.qml'
VISUALIZER_QML = ROOT / 'plugins/visualizer/Visualizer.qml'

SAMPLE_SPECTRUM = [
    0.82, 0.88, 0.94, 0.86, 0.75, 0.68, 0.62, 0.58,
    0.64, 0.72, 0.85, 0.91, 0.84, 0.76, 0.67, 0.59,
    0.52, 0.48, 0.55, 0.66, 0.78, 0.83, 0.74, 0.63,
    0.54, 0.46, 0.41, 0.49, 0.61, 0.71, 0.77, 0.69,
    0.58, 0.49, 0.42, 0.37, 0.44, 0.53, 0.64, 0.68,
    0.59, 0.50, 0.41, 0.34, 0.29, 0.36, 0.45, 0.54,
    0.58, 0.49, 0.39, 0.31, 0.26, 0.22, 0.28, 0.35,
    0.42, 0.38, 0.30, 0.24, 0.19, 0.15, 0.12, 0.09,
]

DARK_PALETTE = {
    'backdropTop': '#111319',
    'backdropBottom': '#181c26',
    'panelSurface': '#e8171a23',
    'panelBorder': '#2bffffff',
    'background': '#161821',
    'foreground': '#ebeef5',
    'accent': '#d5b55c',
    'color1': '#e06c75',
    'color3': '#e5c07b',
    'color4': '#61afef',
    'color5': '#c678dd',
    'radius': 12,
    'fontFamily': 'sans-serif',
}

LIGHT_PALETTE = {
    'backdropTop': '#e7ecf3',
    'backdropBottom': '#dce3ec',
    'panelSurface': '#e8f5f7fa',
    'panelBorder': '#26000000',
    'background': '#f4f6f9',
    'foreground': '#1a1d24',
    'accent': '#9c7618',
    'color1': '#c93b4b',
    'color3': '#b58114',
    'color4': '#2563eb',
    'color5': '#9333ea',
    'radius': 12,
    'fontFamily': 'sans-serif',
}

SAMPLE_HARDWARE = {
    'status': 'ready',
    'error': '',
    'identity': {},
    'sections': [
        {
            'title': 'CPU',
            'name': 'AMD Ryzen 7 7840U',
            'usage': 28,
            'rows': [
                ['Cores / threads', '8 / 16'],
                ['Frequency / temperature', '3.85 GHz · 52°C'],
            ],
        },
        {
            'title': 'GPU',
            'name': 'AMD Radeon 780M',
            'usage': 18,
            'rows': [
                ['VRAM used / total', '1.2 / 4.0 GiB'],
                ['Temperature', '47.0 °C'],
            ],
        },
        {
            'title': 'RAM',
            'name': 'Memory',
            'usage': 78,
            'rows': [
                ['Used / total', '24.4 GiB / 31.3 GiB'],
                ['Available', '6.9 GiB'],
            ],
        },
        {
            'title': 'Storage',
            'name': 'Root',
            'usage': 48,
            'rows': [
                ['Type / device', 'NVMe SSD · nvme0n1'],
                ['Used / total', '220 GiB / 460 GiB'],
                ['Free', '240 GiB'],
            ],
        },
    ],
    'network': {
        'status': 'ready',
        'download': 12400000,
        'upload': 1800000,
        'interfaces': ['enp4s0'],
        'connection': 'Wired',
    },
}


def build_harness(scene):
    palette = DARK_PALETTE if scene['theme'] == 'dark' else LIGHT_PALETTE
    outer_w = scene['widget_width'] + 48
    outer_h = scene['widget_height'] + 48
    if scene['kind'] == 'notes':
        qml_path = NOTES_QML
    elif scene['kind'] == 'visualizer':
        qml_path = VISUALIZER_QML
    else:
        qml_path = HARDWARE_QML
    api_hardware = 'null'
    if scene['kind'] == 'hardware':
        api_hardware = json.dumps(scene.get('hardware', SAMPLE_HARDWARE))
    api_spectrum = json.dumps(scene.get('spectrum', SAMPLE_SPECTRUM if scene['kind'] == 'visualizer' else []))
    audio_active = 'true' if scene.get('audio_active', scene['kind'] == 'visualizer') else 'false'
    saved = scene.get('saved', {})
    saved_json = json.dumps(saved)
    use_panel = 'true' if scene.get('surface', 'panel' if scene['kind'] == 'hardware' else 'none') == 'panel' else 'false'
    if scene['kind'] == 'visualizer':
        loader_props = json.dumps({
            'persistOptions': False,
            'style': saved.get('style', 'wave'),
            'colors': saved.get('colors', 'accent'),
        })[1:-1]
    else:
        loader_props = '"persistData": false'

    return f"""import QtQuick
import QtQuick.Window
import Quickshell
import "{qml_path.parent.as_uri()}" as WidgetPlugin

ShellRoot {{
    Window {{
        id: win
        width: {outer_w}
        height: {outer_h}
        visible: true
        color: "{palette['backdropTop']}"

        Rectangle {{
            id: stage
            width: {outer_w}
            height: {outer_h}
            gradient: Gradient {{
                GradientStop {{ position: 0.0; color: "{palette['backdropTop']}" }}
                GradientStop {{ position: 1.0; color: "{palette['backdropBottom']}" }}
            }}

            Rectangle {{
                id: frame
                anchors.centerIn: parent
                width: {scene['widget_width']}
                height: {scene['widget_height']}
                radius: {palette['radius']}
                color: {use_panel} ? "{palette['panelSurface']}" : "transparent"
                border.width: {use_panel} ? 1 : 0
                border.color: "{palette['panelBorder']}"

                QtObject {{
                    id: mockApi
                    property string pluginId: "{scene['plugin_id']}"
                    property string entryId: "{scene['entry_id']}"
                    property string instance: "render-preview"
                    property string surface: "{scene['surface']}"
                    property string title: "{scene['title']}"
                    property string detail: ""
                    property bool compact: false
                    property bool editing: false
                    property bool acceptsKeyboard: false
                    property bool keyboardFocus: false
                    property color background: "{palette['background']}"
                    property color foreground: "{palette['foreground']}"
                    property color accent: "{palette['accent']}"
                    property var palette: ({{
                        surface: "{palette['panelSurface']}",
                        color1: "{palette['color1']}",
                        color3: "{palette['color3']}",
                        color4: "{palette['color4']}",
                        color5: "{palette['color5']}"
                    }})
                    property real radius: {palette['radius']}
                    property real spacing: 8
                    property string fontFamily: "{palette['fontFamily']}"
                    property real headingSize: 16
                    property real bodySize: 13
                    property real captionSize: 11
                    property var instanceData: ({saved_json})
                    property bool instanceDataReady: true
                    property var hardware: ({api_hardware})
                    property int spectrumBars: 64
                    property int spectrumFrameRate: 30
                    property bool spectrumSmoothing: false
                    property var spectrum: ({api_spectrum})
                    property bool audioActive: {audio_active}
                    signal instanceDataLoaded()
                    signal keyboardReleased()
                    signal menuTriggered(string id)
                    function setMenu(entries) {{}}
                    function saveInstanceData(value) {{}}
                    function releaseKeyboard() {{ keyboardFocus = false; }}
                }}

                Loader {{
                    id: loader
                    anchors.fill: parent
                    Component.onCompleted: setSource("{qml_path.as_uri()}", {{
                        api: mockApi,
                        {loader_props}
                    }})
                    onStatusChanged: {{
                        if (status === Loader.Error) {{
                            console.error("Failed to load widget QML");
                            Qt.exit(3);
                        }}
                    }}
                }}
            }}
        }}

        Timer {{
            interval: 120
            running: true
            repeat: false
            onTriggered: {{
                stage.grabToImage(function(result) {{
                    const ok = result.saveToFile("{scene['out_path']}");
                    if (!ok) {{
                        console.error("Failed to save render to {scene['out_path']}");
                        Qt.exit(2);
                        return;
                    }}
                    Qt.quit();
                }});
            }}
        }}
    }}
}}
"""


def default_scenes(out_dir):
    out_dir = Path(out_dir)
    note_sample = {
        'color': 'yellow',
        'text': (
            'Desktop widget notes\n'
            '- Saved per note copy\n'
            '- Soft dark & light colors\n'
            '- Click anywhere to type; Esc returns to desktop'
        ),
    }
    return [
        {
            'name': 'notes-dark.png',
            'kind': 'notes',
            'theme': 'dark',
            'plugin_id': 'notes',
            'entry_id': 'note',
            'title': 'Note',
            'surface': 'none',
            'widget_width': 260,
            'widget_height': 240,
            'saved': note_sample,
            'out_path': str(out_dir / 'notes-dark.png'),
        },
        {
            'name': 'notes-light.png',
            'kind': 'notes',
            'theme': 'light',
            'plugin_id': 'notes',
            'entry_id': 'note',
            'title': 'Note',
            'surface': 'none',
            'widget_width': 260,
            'widget_height': 240,
            'saved': note_sample,
            'out_path': str(out_dir / 'notes-light.png'),
        },
        {
            'name': 'hardware-compact-dark.png',
            'kind': 'hardware',
            'theme': 'dark',
            'plugin_id': 'hardware',
            'entry_id': 'hardware',
            'title': 'Hardware',
            'surface': 'panel',
            'widget_width': 480,
            'widget_height': 96,
            'saved': {'mode': 'compact'},
            'out_path': str(out_dir / 'hardware-compact-dark.png'),
        },
        {
            'name': 'hardware-compact-light.png',
            'kind': 'hardware',
            'theme': 'light',
            'plugin_id': 'hardware',
            'entry_id': 'hardware',
            'title': 'Hardware',
            'surface': 'panel',
            'widget_width': 480,
            'widget_height': 96,
            'saved': {'mode': 'compact'},
            'out_path': str(out_dir / 'hardware-compact-light.png'),
        },
        {
            'name': 'hardware-detailed-dark.png',
            'kind': 'hardware',
            'theme': 'dark',
            'plugin_id': 'hardware',
            'entry_id': 'hardware',
            'title': 'Hardware',
            'surface': 'panel',
            'widget_width': 480,
            'widget_height': 280,
            'saved': {'mode': 'detailed'},
            'out_path': str(out_dir / 'hardware-detailed-dark.png'),
        },
        {
            'name': 'hardware-detailed-light.png',
            'kind': 'hardware',
            'theme': 'light',
            'plugin_id': 'hardware',
            'entry_id': 'hardware',
            'title': 'Hardware',
            'surface': 'panel',
            'widget_width': 480,
            'widget_height': 280,
            'saved': {'mode': 'detailed'},
            'out_path': str(out_dir / 'hardware-detailed-light.png'),
        },
    ]


def visualizer_scenes(out_dir, styles=('wave', 'bars', 'ring', 'mirror', 'dots'),
                      shapes=(('square', 240, 240), ('wide', 900, 180)),
                      themes=('dark', 'light'), colors='accent'):
    out_dir = Path(out_dir)
    scenes = []
    for style in styles:
        for shape_name, width, height in shapes:
            for theme in themes:
                filename = f'visualizer-{style}-{shape_name}-{theme}.png'
                scenes.append({
                    'name': filename,
                    'kind': 'visualizer',
                    'theme': theme,
                    'plugin_id': 'visualizer',
                    'entry_id': 'visualizer',
                    'title': 'Visualizer',
                    'surface': 'none',
                    'widget_width': width,
                    'widget_height': height,
                    'saved': {'style': style, 'colors': colors},
                    'out_path': str(out_dir / filename),
                })
    return scenes


def render_scenes_batch(scenes, quickshell_bin='quickshell'):
    if not scenes:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        items_qml = []
        captures_js = []
        for idx, scene in enumerate(scenes):
            palette = DARK_PALETTE if scene['theme'] == 'dark' else LIGHT_PALETTE
            outer_w = scene['widget_width'] + 48
            outer_h = scene['widget_height'] + 48
            if scene['kind'] == 'notes':
                qml_path = NOTES_QML
            elif scene['kind'] == 'visualizer':
                qml_path = VISUALIZER_QML
            else:
                qml_path = HARDWARE_QML
            api_hardware = 'null'
            if scene['kind'] == 'hardware':
                api_hardware = json.dumps(scene.get('hardware', SAMPLE_HARDWARE))
            api_spectrum = json.dumps(scene.get('spectrum', SAMPLE_SPECTRUM if scene['kind'] == 'visualizer' else []))
            audio_active = 'true' if scene.get('audio_active', scene['kind'] == 'visualizer') else 'false'
            saved = scene.get('saved', {})
            saved_json = json.dumps(saved)
            use_panel = 'true' if scene.get('surface', 'panel' if scene['kind'] == 'hardware' else 'none') == 'panel' else 'false'
            if scene['kind'] == 'visualizer':
                loader_props = json.dumps({
                    'persistOptions': False,
                    'style': saved.get('style', 'wave'),
                    'colors': saved.get('colors', 'accent'),
                })[1:-1]
            else:
                loader_props = '"persistData": false'
            Path(scene['out_path']).parent.mkdir(parents=True, exist_ok=True)
            items_qml.append(f"""
        Rectangle {{
            id: stage_{idx}
            x: 0
            y: {idx * 1200}
            width: {outer_w}
            height: {outer_h}
            gradient: Gradient {{
                GradientStop {{ position: 0.0; color: "{palette['backdropTop']}" }}
                GradientStop {{ position: 1.0; color: "{palette['backdropBottom']}" }}
            }}
            Rectangle {{
                anchors.centerIn: parent
                width: {scene['widget_width']}
                height: {scene['widget_height']}
                radius: {palette['radius']}
                color: {use_panel} ? "{palette['panelSurface']}" : "transparent"
                border.width: {use_panel} ? 1 : 0
                border.color: "{palette['panelBorder']}"
                QtObject {{
                    id: api_{idx}
                    property string pluginId: "{scene['plugin_id']}"
                    property string entryId: "{scene['entry_id']}"
                    property string instance: "render-preview-{idx}"
                    property string surface: "{scene['surface']}"
                    property string title: "{scene['title']}"
                    property string detail: ""
                    property bool compact: false
                    property bool editing: false
                    property bool acceptsKeyboard: false
                    property bool keyboardFocus: false
                    property color background: "{palette['background']}"
                    property color foreground: "{palette['foreground']}"
                    property color accent: "{palette['accent']}"
                    property var palette: ({{
                        surface: "{palette['panelSurface']}",
                        color1: "{palette['color1']}",
                        color3: "{palette['color3']}",
                        color4: "{palette['color4']}",
                        color5: "{palette['color5']}"
                    }})
                    property real radius: {palette['radius']}
                    property real spacing: 8
                    property string fontFamily: "{palette['fontFamily']}"
                    property real headingSize: 16
                    property real bodySize: 13
                    property real captionSize: 11
                    property var instanceData: ({saved_json})
                    property bool instanceDataReady: true
                    property var hardware: ({api_hardware})
                    property int spectrumBars: 64
                    property int spectrumFrameRate: 30
                    property bool spectrumSmoothing: false
                    property var spectrum: ({api_spectrum})
                    property bool audioActive: {audio_active}
                    signal instanceDataLoaded()
                    signal keyboardReleased()
                    signal menuTriggered(string id)
                    function setMenu(entries) {{}}
                    function saveInstanceData(value) {{}}
                    function releaseKeyboard() {{ keyboardFocus = false; }}
                }}
                Loader {{
                    anchors.fill: parent
                    Component.onCompleted: setSource("{qml_path.as_uri()}", {{
                        api: api_{idx},
                        {loader_props}
                    }})
                    onStatusChanged: {{
                        if (status === Loader.Error) {{
                            console.error("Failed to load widget QML in scene {idx}");
                            Qt.exit(3);
                        }}
                    }}
                }}
            }}
        }}""")
            captures_js.append(f'{{item: stage_{idx}, path: {json.dumps(scene["out_path"])}}}')

        harness = tmp_path / 'batch_harness.qml'
        harness.write_text(f"""import QtQuick
import QtQuick.Window
import Quickshell

ShellRoot {{
    Window {{
        width: 1024
        height: 1024
        visible: true
        color: "#111319"
        {''.join(items_qml)}
        Timer {{
            interval: 150
            running: true
            repeat: false
            onTriggered: {{
                const targets = [{', '.join(captures_js)}];
                let index = 0;
                function nextCapture() {{
                    if (index >= targets.length) {{
                        Qt.quit();
                        return;
                    }}
                    const current = targets[index++];
                    current.item.grabToImage(function(result) {{
                        if (!result.saveToFile(current.path)) {{
                            console.error("Failed to save " + current.path);
                            Qt.exit(2);
                            return;
                        }}
                        nextCapture();
                    }});
                }}
                nextCapture();
            }}
        }}
    }}
}}
""", encoding='utf-8')
        env = os.environ.copy()
        env['QT_QPA_PLATFORM'] = 'offscreen'
        env['HOME'] = str(tmp_path / 'home')
        env['XDG_CONFIG_HOME'] = str(tmp_path / 'config')
        env['XDG_DATA_HOME'] = str(tmp_path / 'data')
        env['XDG_STATE_HOME'] = str(tmp_path / 'state')
        env['XDG_RUNTIME_DIR'] = str(tmp_path / 'runtime')
        for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_RUNTIME_DIR'):
            Path(env[key]).mkdir(parents=True, exist_ok=True)
        os.chmod(env['XDG_RUNTIME_DIR'], 0o700)
        result = subprocess.run(
            [quickshell_bin, '-p', str(harness), '--no-duplicate'],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"quickshell batch failed ({result.returncode}): {result.stderr}\n{result.stdout}")
        outputs = []
        for scene in scenes:
            out = Path(scene['out_path'])
            if not out.is_file() or out.stat().st_size == 0:
                raise RuntimeError(f"missing render output: {out}")
            outputs.append(out)
        return outputs


def render_scene(scene, quickshell_bin='quickshell'):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        harness = tmp_path / 'harness.qml'
        harness.write_text(build_harness(scene), encoding='utf-8')
        env = os.environ.copy()
        env['QT_QPA_PLATFORM'] = 'offscreen'
        env['HOME'] = str(tmp_path / 'home')
        env['XDG_CONFIG_HOME'] = str(tmp_path / 'config')
        env['XDG_DATA_HOME'] = str(tmp_path / 'data')
        env['XDG_STATE_HOME'] = str(tmp_path / 'state')
        env['XDG_RUNTIME_DIR'] = str(tmp_path / 'runtime')
        for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_RUNTIME_DIR'):
            Path(env[key]).mkdir(parents=True, exist_ok=True)
        os.chmod(env['XDG_RUNTIME_DIR'], 0o700)
        Path(scene['out_path']).parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [quickshell_bin, '-p', str(harness), '--no-duplicate'],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"quickshell failed ({result.returncode}): {result.stderr}\n{result.stdout}")
        out = Path(scene['out_path'])
        if not out.is_file() or out.stat().st_size == 0:
            raise RuntimeError(f"missing render output: {out}")
        return out


def render_all(out_dir):
    quickshell_bin = shutil.which('quickshell')
    if not quickshell_bin:
        raise RuntimeError('quickshell binary not found')
    return [render_scene(scene, quickshell_bin=quickshell_bin) for scene in default_scenes(out_dir)]


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / 'renders'
    outputs = render_all(target)
    for item in outputs:
        print(item)
