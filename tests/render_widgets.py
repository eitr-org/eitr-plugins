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

DARK_PALETTE = {
    'backdropTop': '#111319',
    'backdropBottom': '#181c26',
    'panelSurface': '#e8171a23',
    'panelBorder': '#2bffffff',
    'background': '#161821',
    'foreground': '#ebeef5',
    'accent': '#d5b55c',
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
    qml_path = NOTES_QML if scene['kind'] == 'notes' else HARDWARE_QML
    api_hardware = 'null'
    if scene['kind'] == 'hardware':
        api_hardware = json.dumps(scene.get('hardware', SAMPLE_HARDWARE))
    saved_json = json.dumps(scene.get('saved', {}))
    use_panel = 'true' if scene['kind'] == 'hardware' else 'false'

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
                    property var palette: ({{ surface: "{palette['panelSurface']}" }})
                    property real radius: {palette['radius']}
                    property real spacing: 8
                    property string fontFamily: "{palette['fontFamily']}"
                    property real headingSize: 16
                    property real bodySize: 13
                    property real captionSize: 11
                    property var instanceData: ({saved_json})
                    property bool instanceDataReady: true
                    property var hardware: ({api_hardware})
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
                        persistData: false
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
