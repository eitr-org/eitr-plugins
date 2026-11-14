"""Status parsing and offscreen QML panel render tests for WireGuard and NetworkManager VPN."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent / 'eitr'


def load_plugin(identifier, filename='status.py'):
    from test_plugins import load
    return load(identifier, filename)


class WireGuardStatusTests(unittest.TestCase):
    def setUp(self):
        self.status = load_plugin('wireguard', 'status.py')

    def test_summarize_none_when_no_tunnels_exist(self):
        summary = self.status.summarize('', '', backend='networkmanager')
        self.assertEqual(summary['state'], 'disconnected')
        self.assertEqual(summary['backend'], 'networkmanager')
        self.assertEqual(summary['activeTunnel'], '')
        self.assertEqual(summary['tunnelCount'], 0)
        self.assertEqual(summary['tunnels'], [])

    def test_summarize_several_tunnels_from_wg_show_and_nmcli(self):
        wg_show = (
            'interface: office\n'
            '  public key: pub1\n'
            '  private key: (hidden)\n'
            '  listening port: 51820\n\n'
            'peer: peerA\n'
            '  endpoint: 198.51.100.10:51820\n'
            '  allowed ips: 10.20.0.0/24, 10.20.1.0/24\n'
            '  latest handshake: 35 seconds ago\n'
            '  transfer: 1.50 MiB received, 512.00 KiB sent\n\n'
            'peer: peerB\n'
            '  endpoint: 198.51.100.11:51820\n'
            '  allowed ips: 10.20.2.0/24\n'
        )
        nm_lines = (
            '11111111-1111-1111-1111-111111111111:wireguard:yes:activated:office:office\n'
            '22222222-2222-2222-2222-222222222222:wireguard:no::--:homelab\n'
            '33333333-3333-3333-3333-333333333333:wireguard:no:activating:staging:staging\n'
            '44444444-4444-4444-4444-444444444444:802-3-ethernet:yes:activated:eth0:Wired\n'
        )
        summary = self.status.summarize(wg_show, nm_lines, backend='networkmanager', active_links='backup UP\n')
        self.assertEqual(summary['state'], 'connected')
        self.assertEqual(summary['activeTunnel'], 'office')
        self.assertEqual(summary['endpoint'], '198.51.100.10:51820')
        self.assertEqual(summary['transfer'], '1.50 MiB received, 512.00 KiB sent')
        self.assertEqual(summary['handshake'], '35 seconds ago')
        self.assertEqual([item['name'] for item in summary['tunnels']], ['office', 'backup', 'homelab', 'staging'])
        staging = next(item for item in summary['tunnels'] if item['name'] == 'staging')
        self.assertEqual(staging['state'], 'connecting')

        dump = 'wg0\tpriv\tpub\t51820\toff\nwg0\tpeer\t(none)\t203.0.113.5:51820\t10.0.0.0/24\t1700000000\t2048\t1024\toff\n'
        parsed_dump = self.status.parse_wg_show(dump)
        self.assertEqual(parsed_dump['wg0']['endpoint'], '203.0.113.5:51820')
        self.assertEqual(parsed_dump['wg0']['transfer'], '2.00 KiB received, 1.00 KiB sent')

    def test_read_handles_missing_binary_errors_and_bounds(self):
        with patch.object(self.status.shutil, 'which', return_value=None):
            result = self.status.read()
        self.assertEqual((result['installed'], result['state']), (False, 'not-installed'))

        with patch.object(self.status.shutil, 'which', return_value='/usr/bin/wg'), \
             patch.object(self.status, 'nm_active', return_value=False), \
             patch.object(self.status, 'saved_wg_quick_profiles', return_value=[]), \
             patch.object(self.status.subprocess, 'run', return_value=Mock(returncode=1, stdout='')) as command:
            result = self.status.read()
        self.assertEqual(result['state'], 'unavailable')
        self.assertTrue(all(call.kwargs['timeout'] <= 3 for call in command.call_args_list))

        many = [{'id': f'wg-{index}', 'name': f'tunnel-{index:03d}', 'connected': False} for index in range(500)]
        summary = self.status.summarize({}, many, backend='wg-quick')
        self.assertEqual(len(summary['tunnels']), self.status.TUNNEL_LIMIT)
        self.assertEqual(summary['tunnelCount'], 500)
        self.assertLess(len(json.dumps(summary)), 64 * 1024)


class NetworkManagerVpnStatusTests(unittest.TestCase):
    def setUp(self):
        self.status = load_plugin('networkmanager-vpn', 'status.py')

    def test_parse_none_when_only_non_vpn_connections_exist(self):
        raw = '11111111-1111-1111-1111-111111111111:802-3-ethernet:yes:activated:eth0:Wired\n'
        summary = self.status.summarize(raw, '')
        self.assertEqual(summary['state'], 'disconnected')
        self.assertEqual(summary['profileCount'], 0)
        self.assertEqual(summary['profiles'], [])

    def test_summarize_several_profiles_and_active_details(self):
        raw = (
            '11111111-1111-1111-1111-111111111111:vpn:yes:activated:tun0:Corp\\: West\n'
            '22222222-2222-2222-2222-222222222222:vpn:no::--:Uni VPN\n'
            '33333333-3333-3333-3333-333333333333:wireguard:no::--:Home WG\n'
            '44444444-4444-4444-4444-444444444444:802-3-ethernet:yes:activated:eth0:Wired\n'
        )
        details = (
            'connection.uuid:11111111-1111-1111-1111-111111111111\n'
            'connection.id:Corp\\: West\n'
            'connection.type:vpn\n'
            'vpn.service-type:org.freedesktop.NetworkManager.openvpn\n'
            'vpn.data:remote = vpn.corp.example:1194, connection-type = tls\n'
            'GENERAL.STATE:activated\n'
            'GENERAL.DEVICES:tun0\n'
            'IP4.ADDRESS[1]:10.8.0.6/24\n'
            'IP4.GATEWAY:10.8.0.1\n'
            'IP4.DNS[1]:10.8.0.1\n'
            'connection.uuid:22222222-2222-2222-2222-222222222222\n'
            'connection.id:Uni VPN\n'
            'connection.type:vpn\n'
            'vpn.service-type:org.freedesktop.NetworkManager.openconnect\n'
            'vpn.data:gateway = vpn.uni.example\n'
        )
        summary = self.status.summarize(raw, details)
        self.assertEqual(summary['state'], 'connected')
        self.assertEqual(summary['activeProfile'], 'Corp: West')
        self.assertEqual(summary['protocol'], 'OpenVPN')
        self.assertEqual(summary['interface'], 'tun0')
        self.assertEqual(summary['address'], '10.8.0.6')
        self.assertEqual(summary['gateway'], '10.8.0.1')
        self.assertEqual(summary['endpoint'], 'vpn.corp.example:1194')
        self.assertEqual(summary['dns'], '10.8.0.1')
        self.assertEqual([item['name'] for item in summary['profiles']], ['Corp: West', 'Home WG', 'Uni VPN'])
        self.assertEqual([item['typeLabel'] for item in summary['profiles']], ['OpenVPN', 'WireGuard', 'OpenConnect'])

    def test_read_reports_iwd_missing_nmcli_errors_and_bounds(self):
        with patch.object(self.status.shutil, 'which', return_value=None):
            self.assertEqual(self.status.read()['state'], 'not-installed')
        with patch.object(self.status.shutil, 'which', return_value='/usr/bin/nmcli'), \
             patch.object(self.status, 'nm_active', return_value=False):
            result = self.status.read()
        self.assertEqual((result['state'], result['backend']), ('iwd', 'iwd'))

        with patch.object(self.status.shutil, 'which', return_value='/usr/bin/nmcli'), \
             patch.object(self.status, 'nm_active', return_value=True), \
             patch.object(self.status.subprocess, 'run', return_value=Mock(returncode=1, stdout='')) as command:
            self.assertEqual(self.status.read()['state'], 'unavailable')
        self.assertTrue(all(call.kwargs['timeout'] <= 3 for call in command.call_args_list))

        many = [{'id': f'{index:08x}-1111-1111-1111-111111111111', 'name': f'vpn-{index}',
                 'kind': 'vpn', 'connected': False, 'state': 'disconnected', 'interface': ''} for index in range(500)]
        summary = self.status.summarize(many, {})
        self.assertEqual(len(summary['profiles']), self.status.PROFILE_LIMIT)
        self.assertEqual(summary['profileCount'], 500)
        self.assertLess(len(json.dumps(summary)), 64 * 1024)


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required')
class PanelRenderTests(unittest.TestCase):
    def test_wireguard_and_networkmanager_vpn_panels_render_in_dark_and_light(self):
        wg_folder = (ROOT / 'plugins/wireguard').as_uri()
        nm_folder = (ROOT / 'plugins/networkmanager-vpn').as_uri()
        wg_data = {
            'installed': True,
            'state': 'connected',
            'backend': 'networkmanager',
            'activeTunnel': 'office',
            'interface': 'office',
            'endpoint': '198.51.100.10:51820',
            'transfer': '14.20 MiB received, 3.80 MiB sent',
            'handshake': '24 seconds ago',
            'tunnelCount': 3,
            'tunnels': [
                {'id': 'office', 'name': 'office', 'interface': 'office', 'state': 'connected',
                 'connected': True, 'endpoint': '198.51.100.10:51820',
                 'transfer': '14.20 MiB received, 3.80 MiB sent', 'handshake': '24 seconds ago'},
                {'id': 'homelab', 'name': 'homelab', 'interface': '', 'state': 'disconnected',
                 'connected': False, 'endpoint': '203.0.113.12:51820', 'transfer': '', 'handshake': ''},
                {'id': 'staging', 'name': 'staging', 'interface': '', 'state': 'disconnected',
                 'connected': False, 'endpoint': '', 'transfer': '', 'handshake': ''},
            ],
        }
        nm_data = {
            'installed': True,
            'state': 'connected',
            'backend': 'networkmanager',
            'activeProfile': 'Corp West',
            'protocol': 'OpenVPN',
            'interface': 'tun0',
            'address': '10.8.0.6',
            'gateway': '10.8.0.1',
            'endpoint': 'vpn.corp.example:1194',
            'dns': '10.8.0.1',
            'profileCount': 3,
            'profiles': [
                {'id': '11111111-1111-1111-1111-111111111111', 'name': 'Corp West',
                 'protocol': 'openvpn', 'typeLabel': 'OpenVPN', 'state': 'connected',
                 'connected': True, 'interface': 'tun0', 'address': '10.8.0.6',
                 'gateway': '10.8.0.1', 'endpoint': 'vpn.corp.example:1194', 'dns': '10.8.0.1'},
                {'id': '22222222-2222-2222-2222-222222222222', 'name': 'Home WireGuard',
                 'protocol': 'wireguard', 'typeLabel': 'WireGuard', 'state': 'disconnected',
                 'connected': False, 'interface': '', 'address': '',
                 'gateway': '', 'endpoint': 'wg.home.example:51820', 'dns': ''},
                {'id': '33333333-3333-3333-3333-333333333333', 'name': 'University AnyConnect',
                 'protocol': 'openconnect', 'typeLabel': 'OpenConnect', 'state': 'disconnected',
                 'connected': False, 'interface': '', 'address': '',
                 'gateway': '', 'endpoint': 'vpn.uni.example', 'dns': ''},
            ],
        }
        nm_iwd_data = dict(nm_data, state='iwd', backend='iwd', activeProfile='', profiles=[], profileCount=0)
        with tempfile.TemporaryDirectory(prefix='eitr-vpn-renders-') as directory:
            output_dir = Path(os.environ.get('EITR_PLUGIN_RENDERS', directory))
            output_dir.mkdir(parents=True, exist_ok=True)
            for plugin_kind, folder_uri in (('wireguard', wg_folder), ('networkmanager-vpn', nm_folder)):
                for theme in ('dark', 'light'):
                    capture = output_dir / f'{plugin_kind}-{theme}.png'
                    background, foreground, accent = (
                        ('#18212b', '#e9eef1', '#7ee0b5') if theme == 'dark'
                        else ('#f5f0e7', '#252936', '#2a8568')
                    )
                    canvas = '#0e151e' if theme == 'dark' else '#e2dfd5'
                    panel_qml = 'WireGuardPanel' if plugin_kind == 'wireguard' else 'VpnPanel'
                    icon_qml = 'WireGuardBarIcon' if plugin_kind == 'wireguard' else 'VpnBarIcon'
                    primary = wg_data if plugin_kind == 'wireguard' else nm_data
                    secondary = wg_data if plugin_kind == 'wireguard' else nm_iwd_data
                    confirm_snippet = 'panelSecondary.requestRemove("staging", "staging");' if plugin_kind == 'wireguard' else ''
                    secondary_title = 'Inline remove confirmation' if plugin_kind == 'wireguard' else 'When desktop uses iwd'
                    fixture = Path(directory) / f'{plugin_kind}-{theme}.qml'
                    fixture.write_text(f'''import QtQuick
import Quickshell
import "{folder_uri}" as PluginUi
ShellRoot {{
    FloatingWindow {{
        visible: true; implicitWidth: 880; implicitHeight: 540
        Rectangle {{
            id: sample; anchors.fill: parent; color: "{canvas}"
            QtObject {{
                id: apiPrimary
                property string dataText: {json.dumps(json.dumps(primary))}
                property string dataError: ""
                property color foreground: "{foreground}"
                property color background: "{background}"
                property color accent: "{accent}"
                property string fontFamily: "sans-serif"
                property int headingSize: 14
                property int bodySize: 13
                property int captionSize: 11
                property real radius: 6
                function runDataCommand() {{}}
            }}
            QtObject {{
                id: apiSecondary
                property string dataText: {json.dumps(json.dumps(secondary))}
                property string dataError: ""
                property color foreground: "{foreground}"
                property color background: "{background}"
                property color accent: "{accent}"
                property string fontFamily: "sans-serif"
                property int headingSize: 14
                property int bodySize: 13
                property int captionSize: 11
                property real radius: 6
                function runDataCommand() {{}}
            }}
            Row {{
                x: 28; y: 18; spacing: 10
                Rectangle {{
                    width: 34; height: 28; radius: 6; color: "{background}"
                    border.width: 1; border.color: Qt.alpha("{foreground}", 0.14)
                    PluginUi.{icon_qml} {{
                        id: barIconConnected
                        anchors.centerIn: parent; api: apiPrimary
                    }}
                }}
                Rectangle {{
                    width: 34; height: 28; radius: 6; color: "{background}"
                    border.width: 1; border.color: Qt.alpha("{foreground}", 0.14)
                    PluginUi.{icon_qml} {{
                        id: barIconDimmed
                        anchors.centerIn: parent
                        api: QtObject {{
                            property string dataText: '{{"installed":true,"state":"disconnected"}}'
                            property color foreground: "{foreground}"
                            property color background: "{background}"
                        }}
                    }}
                }}
                Text {{
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Bar icons (connected / disconnected) & panel"; color: "{foreground}"; opacity: 0.72; font.pixelSize: 12
                }}
            }}
            Rectangle {{
                x: 28; y: 56; width: 400; height: panelPrimary.implicitHeight + 28
                radius: 12; color: "{background}"
                border.width: 1; border.color: Qt.alpha("{foreground}", 0.12)
                PluginUi.{panel_qml} {{
                    id: panelPrimary; x: 14; y: 14; width: parent.width - 28; api: apiPrimary
                }}
            }}
            Text {{
                x: 452; y: 24; text: "{secondary_title}"
                color: "{foreground}"; opacity: 0.72; font.pixelSize: 12
            }}
            Rectangle {{
                x: 452; y: 56; width: 400; height: panelSecondary.implicitHeight + 28
                radius: 12; color: "{background}"
                border.width: 1; border.color: Qt.alpha("{foreground}", 0.12)
                PluginUi.{panel_qml} {{
                    id: panelSecondary; x: 14; y: 14; width: parent.width - 28; api: apiSecondary
                    Component.onCompleted: {{ {confirm_snippet} }}
                }}
            }}
            Timer {{
                interval: 400; running: true
                onTriggered: {{
                    try {{
                        if (!barIconConnected.connected || barIconDimmed.connected)
                            throw new Error("Bar icon did not detect connected/disconnected state");
                        if (panelPrimary.implicitHeight <= 100 || panelSecondary.implicitHeight <= 60)
                            throw new Error("Panel did not size: " + panelPrimary.implicitHeight);
                        sample.grabToImage(function(result) {{
                            if (!result.saveToFile("{capture}")) {{
                                console.log("FIXTURE_FAILED saveToFile");
                                Qt.exit(1);
                            }}
                            console.log("VPN_PANEL_RENDER_OK");
                            Qt.quit();
                        }});
                    }} catch (error) {{
                        console.log("FIXTURE_FAILED " + error);
                        Qt.exit(1);
                    }}
                }}
            }}
        }}
    }}
}}''')
                    environment = dict(
                        os.environ,
                        QT_QPA_PLATFORM='offscreen',
                        QT_QUICK_BACKEND='software',
                        QML_IMPORT_PATH=str(DESKTOP / 'quickshell'),
                        EITR_CODE_ROOT=str(DESKTOP),
                        XDG_CONFIG_HOME=directory,
                        XDG_STATE_HOME=directory,
                        XDG_DATA_HOME=directory,
                        XDG_CACHE_HOME=directory,
                        XDG_RUNTIME_DIR=directory,
                        DBUS_SESSION_BUS_ADDRESS='unix:path=/nonexistent',
                        HYPRLAND_INSTANCE_SIGNATURE='',
                    )
                    result = subprocess.run(
                        ['quickshell', '--no-color', '-p', str(fixture)],
                        env=environment,
                        text=True,
                        capture_output=True,
                        timeout=15,
                    )
                    output = result.stdout + result.stderr
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn('VPN_PANEL_RENDER_OK', output)
                    self.assertNotIn('FIXTURE_FAILED', output)
                    self.assertNotIn('ReferenceError', output)
                    self.assertNotIn('TypeError', output)
                    self.assertTrue(capture.is_file())
