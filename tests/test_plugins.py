"""Offline tests: no live networking, home writes or privileged commands."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent / 'eitr'
sys.path.insert(0, str(DESKTOP / 'distro/lib'))
sys.path.insert(0, str(ROOT / 'tests'))

from vpn_panel_tests import NetworkManagerVpnStatusTests, PanelRenderTests, WireGuardStatusTests  # noqa: E402,F401


def load(identifier, filename='action.py'):
    runtime = types.ModuleType('runtime')
    for name in ('choose', 'collect', 'launch', 'open_settings', 'open_terminal', 'run', 'Step', 'wait_for_escape'):
        setattr(runtime, name, Mock())
    runtime.ROOT = Path('/usr/share/eitr')
    folder = ROOT / 'plugins' / identifier
    spec = importlib.util.spec_from_file_location(identifier.replace('-', '_') + '_' + Path(filename).stem, folder / filename)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'runtime': runtime}), patch.object(sys, 'path', [str(folder), *sys.path]):
        for sibling in ('status', 'taildrop', 'portal'):
            sys.modules.pop(sibling, None)
        spec.loader.exec_module(module)
    return module


class VPNTests(unittest.TestCase):
    def test_iwd_vpn_refuses_every_action(self):
        for action in ('import', 'up', 'down', 'status'):
            plugin = load('networkmanager-vpn')
            plugin.nm_active = Mock(return_value=False)
            with patch('builtins.print'):
                plugin.main(action)
            plugin.run.assert_not_called()
            plugin.collect.assert_not_called()
            plugin.open_settings.assert_called_once_with()

    def test_profiles_filter_types_and_use_uuid_with_escaped_names(self):
        plugin = load('networkmanager-vpn')
        identifier = '12345678-1234-1234-1234-123456789abc'
        plugin.run.side_effect = [identifier + ':vpn\nother:ethernet\n', 'Name\\: with spaces\n']
        self.assertEqual(plugin.profiles(), [('Name\\: with spaces · ' + identifier, identifier)])
        self.assertEqual(plugin.run.call_args.args[0][-2:], ['uuid', identifier])

    def test_iwd_import_uses_root_importer_and_keeps_keys_off_argv(self):
        plugin = load('wireguard')
        with tempfile.TemporaryDirectory() as temporary:
            filename = Path(temporary) / 'test.conf'
            content = '[Interface]\nPrivateKey = secret\n[Peer]\nPublicKey = public\n'
            filename.write_text(content)
            plugin.collect.return_value = {'file': str(filename)}
            with patch('builtins.print'), patch.object(plugin, 'record_saved_tunnel'):
                plugin.import_profile(False)
        arguments = plugin.run.call_args.args[0]
        self.assertEqual(arguments, ['sudo', '/usr/lib/eitr/eitr-system', 'vpn-import'])
        self.assertNotIn('secret', str(arguments))
        payload = json.loads(plugin.run.call_args.kwargs['input'])
        self.assertFalse(payload['connect'])
        self.assertEqual(payload['backend'], 'wg-quick')

    def test_wireguard_executable_hook_refused_before_import(self):
        plugin = load('wireguard')
        with tempfile.TemporaryDirectory() as temporary:
            filename = Path(temporary) / 'test.conf'
            filename.write_text('[Interface]\nPostUp = malicious\n[Peer]\nPublicKey = public\n')
            plugin.collect.return_value = {'file': str(filename)}
            with self.assertRaises(ValueError):
                plugin.import_profile(False)
        plugin.run.assert_not_called()

    def test_nm_import_cleans_up_if_disabling_autoconnect_fails(self):
        plugin = load('networkmanager-vpn')
        identifier = '12345678-1234-1234-1234-123456789abc'
        with tempfile.TemporaryDirectory() as temporary:
            filename = Path(temporary) / 'test.ovpn'
            filename.write_text('client\n')
            plugin.collect.return_value = {'file': str(filename)}
            plugin.run.side_effect = [identifier, RuntimeError('Failed'), '']
            with self.assertRaises(RuntimeError):
                plugin.import_profile(True)
        self.assertIn('--temporary', plugin.run.call_args_list[0].args[0])
        self.assertEqual(plugin.run.call_args.args[0], ['nmcli', 'connection', 'delete', 'uuid', identifier])

    def test_wg_quick_uses_fixed_absolute_path(self):
        plugin = load('wireguard')
        plugin.nm_active = Mock(return_value=False)
        plugin.collect.return_value = {'name': 'office'}
        with patch('builtins.print'):
            plugin.main('up')
        self.assertEqual(plugin.run.call_args.args[0], ['pkexec', '/usr/bin/wg-quick', 'up', '/etc/wireguard/office.conf'])

    def test_wireguard_panel_actions_and_remove_confirmation(self):
        plugin = load('wireguard')
        identifier = '12345678-1234-1234-1234-123456789abc'
        plugin.nm_active = Mock(return_value=True)
        plugin.run.side_effect = ['wireguard\n', '', 'wireguard\n', '']
        plugin.background(['up', identifier])
        self.assertEqual(plugin.run.call_args_list[1].args[0], ['nmcli', '--wait', '30', 'connection', 'up', 'uuid', identifier])
        plugin.background(['remove', identifier])
        self.assertEqual(plugin.run.call_args.args[0], ['nmcli', 'connection', 'delete', 'uuid', identifier])
        plugin.nm_active = Mock(return_value=False)
        plugin.run.side_effect = None
        plugin.run.return_value = ''
        # A core that lists 'remove' among its root VPN actions gets the clearer eitr-system prompt.
        plugin.run.reset_mock()
        with patch.object(plugin.eitr_vpn, 'ACTIONS', ('import', 'up', 'down', 'remove'), create=True), \
             patch.object(plugin, 'forget_saved_tunnel') as forget:
            plugin.background(['remove', 'office'])
            forget.assert_called_once_with('office')
        self.assertEqual(plugin.run.call_args.args[0], ['pkexec', '/usr/lib/eitr/eitr-system', 'vpn-remove'])
        self.assertEqual(json.loads(plugin.run.call_args.kwargs['input']), {'name': 'office', 'backend': 'wg-quick'})
        plugin.run.reset_mock()
        with patch.object(plugin.eitr_vpn, 'ACTIONS', ('import', 'up', 'down'), create=True), \
             patch.object(plugin, 'forget_saved_tunnel') as forget:
            plugin.background(['remove', 'office'])
            forget.assert_called_once_with('office')
        self.assertEqual(plugin.run.call_args.args[0], ['pkexec', '/usr/bin/rm', '-f', '--', '/etc/wireguard/office.conf'])
        with patch.object(plugin, 'notify'):
            with self.assertRaises(SystemExit):
                plugin.background(['up', '../bad'])
            with self.assertRaises(SystemExit):
                plugin.background(['remove', '../bad'])

    def test_networkmanager_import_takes_the_new_profile_down(self):
        # NetworkManager starts a WireGuard profile as soon as it is added; the import must
        # leave it disconnected, with automatic connection off.
        identifier = 'ad60b436-5e56-4408-8f64-491ea1b1e2cf'
        config = ('[Interface]\nPrivateKey = yAnz5TF+lXXJte14tji3zlMNq+hd2rYUIgJBgB3fBmk=\nAddress = 10.66.0.2/24\n\n'
                  '[Peer]\nPublicKey = xTIBA5rboUvnH4htodjb6e697QjLERt1NAB4mZqp8Dg=\n'
                  'Endpoint = 10.99.0.2:51820\nAllowedIPs = 10.66.0.0/24\n')
        for plugin_id in ('wireguard', 'networkmanager-vpn'):
            plugin = load(plugin_id)
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / 'office.conf'
                path.write_text(config)
                plugin.collect.return_value = {'file': str(path)}
                plugin.run.side_effect = [f"Connection 'office' ({identifier}) successfully added.", '', 'activated\n', '']
                with patch('builtins.print'):
                    plugin.import_profile(True)
            commands = [call.args[0] for call in plugin.run.call_args_list]
            self.assertEqual(commands[1], ['nmcli', 'connection', 'modify', 'uuid', identifier, 'connection.autoconnect', 'no'])
            self.assertEqual(commands[-1], ['nmcli', 'connection', 'down', 'uuid', identifier], plugin_id)

    def test_networkmanager_vpn_panel_actions_and_iwd_settings_route(self):
        plugin = load('networkmanager-vpn')
        identifier = '12345678-1234-1234-1234-123456789abc'
        plugin.nm_active = Mock(return_value=True)
        plugin.run.side_effect = ['vpn\n', '']
        plugin.background(['up', identifier])
        self.assertEqual(plugin.run.call_args.args[0], ['nmcli', '--wait', '30', 'connection', 'up', 'uuid', identifier])
        plugin.run.side_effect = ['vpn\n', '']
        plugin.background(['remove', identifier])
        self.assertEqual(plugin.run.call_args.args[0], ['nmcli', 'connection', 'delete', 'uuid', identifier])
        # Only a VPN profile is ever deleted: an ethernet or Wi-Fi connection is refused.
        plugin.run.side_effect = ['802-3-ethernet\n']
        plugin.run.reset_mock()
        with patch.object(plugin, 'notify'):
            with self.assertRaises(SystemExit):
                plugin.background(['remove', identifier])
            with self.assertRaises(SystemExit):
                plugin.background(['up', 'not-a-uuid'])
        self.assertEqual(plugin.run.call_count, 1)
        plugin.run.side_effect = None
        plugin.nm_active = Mock(return_value=False)
        plugin.background(['up', identifier])
        plugin.open_settings.assert_called_once_with()


class TailscaleTests(unittest.TestCase):
    def test_only_own_online_peers(self):
        plugin = load('tailscale')
        status = {'Self': {'UserID': 1}, 'Peer': {
            'mine': {'UserID': 1, 'Online': True, 'HostName': 'mine', 'TailscaleIPs': ['100.64.0.1']},
            'shared': {'UserID': 2, 'Online': True, 'TailscaleIPs': ['100.64.0.2']},
            'offline': {'UserID': 1, 'Online': False, 'TailscaleIPs': ['100.64.0.3']}}}
        self.assertEqual(plugin.own_online_peers(status), [('mine', '100.64.0.1')])
        self.assertEqual(plugin.own_online_peers({'Self': None, 'Peer': None}), [])

    def test_send_preserves_paths_with_spaces_as_single_arguments(self):
        plugin = load('tailscale')
        with tempfile.TemporaryDirectory() as temporary:
            filename = Path(temporary) / 'file with spaces.txt'
            filename.write_text('payload')
            plugin.collect.return_value = {'files': repr(str(filename))}
            plugin.choose.return_value = '100.64.0.1'
            plugin.run.side_effect = [json.dumps({'BackendState': 'Running', 'Self': {'UserID': 1}}), '']
            with patch.object(plugin.shutil, 'which', return_value='/usr/bin/tailscale'), patch('builtins.print'):
                plugin.main('send')
        self.assertEqual(plugin.run.call_args.args[0], ['tailscale', 'file', 'cp', '--', str(filename), '100.64.0.1:'])
        self.assertEqual(plugin.run.call_args.kwargs['timeout'], 300)

    def test_operator_requires_confirmation_before_sudo(self):
        plugin = load('tailscale')
        plugin.choose.side_effect = RuntimeError('Cancelled')
        with patch.object(plugin.shutil, 'which', return_value='/usr/bin/tailscale'), \
             patch.object(plugin.subprocess, 'run') as command, patch('builtins.print'):
            with self.assertRaises(RuntimeError):
                plugin.main('operator')
        command.assert_not_called()

    def test_panel_actions_open_a_terminal_only_for_steps_that_need_one(self):
        plugin = load('tailscale')
        ready = {'installed': True, 'state': 'disconnected', 'operator': True}
        self.assertIsNone(plugin.next_step('connect', ready))
        self.assertEqual(plugin.next_step('connect', {**ready, 'state': 'signed-out'}), 'login')
        self.assertEqual(plugin.next_step('disconnect', {**ready, 'operator': False}), 'disconnect')
        self.assertEqual(plugin.next_step('connect', {**ready, 'operator': None}), 'connect')
        self.assertEqual(plugin.next_step('connect', {'installed': False, 'state': 'not-installed'}), 'setup')
        self.assertEqual(plugin.next_step('connect', {**ready, 'state': 'unavailable'}), 'setup')

    def test_connect_names_the_operator_and_disconnect_has_no_flags(self):
        plugin = load('tailscale')
        plugin.tailscale_status.read = Mock(return_value={'installed': True, 'state': 'disconnected', 'operator': True})
        with patch.object(plugin.subprocess, 'run', return_value=Mock(returncode=0)) as command, \
             patch.object(plugin.getpass, 'getuser', return_value='person'):
            plugin.background(['connect'])
            self.assertEqual(command.call_args.args[0], ['tailscale', 'up', '--operator=person'])
            plugin.background(['disconnect'])
            self.assertEqual(command.call_args.args[0], ['tailscale', 'down'])
        plugin.open_terminal.assert_not_called()

    def test_signed_out_connect_reopens_in_terminal(self):
        plugin = load('tailscale')
        plugin.tailscale_status.read = Mock(return_value={'installed': True, 'state': 'signed-out', 'operator': True})
        with patch.object(plugin.subprocess, 'run') as command:
            plugin.background(['connect'])
        plugin.open_terminal.assert_called_once_with('login')
        command.assert_not_called()

    def test_send_to_refuses_anything_but_an_address(self):
        plugin = load('tailscale')
        with patch.object(plugin.subprocess, 'run') as command:
            with self.assertRaises(SystemExit):
                plugin.background(['send-to', '--help'])
        self.assertNotIn('file', str(command.call_args_list))

    def test_ping_runs_only_for_an_address(self):
        plugin = load('tailscale')
        with patch.object(plugin.subprocess, 'run') as command:
            with self.assertRaises(RuntimeError):
                plugin.ping('--help')
            command.assert_not_called()
            plugin.ping('100.64.0.9')
        self.assertEqual(command.call_args.args[0], ['tailscale', 'ping', '--c', '3', '--', '100.64.0.9'])

    def test_send_to_passes_chosen_files_as_separate_arguments(self):
        plugin = load('tailscale')
        plugin.tailscale_status.read = Mock(return_value={'peers': [{'name': 'laptop', 'address': '100.64.0.1'}]})
        portal = types.ModuleType('portal')
        with tempfile.TemporaryDirectory() as temporary:
            files = [Path(temporary) / 'a b.txt', Path(temporary) / '-c.txt']
            for filename in files:
                filename.write_text('payload')
            portal.choose_files = Mock(return_value=files)
            with patch.dict(sys.modules, {'portal': portal}), \
                 patch.object(plugin.subprocess, 'run', return_value=Mock(returncode=0)) as command:
                plugin.background(['send-to', '100.64.0.1'])
        copy = next(call.args[0] for call in command.call_args_list if call.args[0][:3] == ['tailscale', 'file', 'cp'])
        self.assertEqual(copy, ['tailscale', 'file', 'cp', '--', *map(str, files), '100.64.0.1:'])

    def test_receive_names_files_and_does_not_request_overwrite(self):
        taildrop = load('tailscale', 'taildrop.py')
        with tempfile.TemporaryDirectory() as temporary:
            inbox = Path(temporary) / 'Taildrop'
            def command(arguments, **kwargs):
                if arguments[:3] == ['tailscale', 'file', 'get']:
                    (inbox / 'received.txt').write_text('received')
                return Mock(returncode=0)
            with patch.object(taildrop.subprocess, 'run', side_effect=command) as runner:
                self.assertEqual(taildrop.fetch(wait=False, inbox=inbox), ['received.txt'])
        self.assertIn('--conflict=rename', runner.call_args.args[0])
        self.assertNotIn('--conflict=overwrite', str(runner.call_args_list))

    def test_receive_service_backs_off_instead_of_failing(self):
        service = load('tailscale', 'receive.py')
        service.fetch = Mock(side_effect=[RuntimeError('denied'), RuntimeError('denied'), ['photo.jpg']])
        service.announce = Mock()
        sleep = Mock()
        with patch.object(service.shutil, 'which', return_value='/usr/bin/tailscale'):
            service.receive_forever(sleep=sleep, rounds=3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 10])
        service.announce.assert_called_once_with(['photo.jpg'])


class TailscaleStatusTests(unittest.TestCase):
    def setUp(self):
        self.status = load('tailscale', 'status.py')

    def test_summary_sorts_online_first_and_marks_taildrop_targets(self):
        sample = {'BackendState': 'Running', 'TailscaleIPs': ['100.64.0.10', 'fd7a::10'],
                  'CurrentTailnet': {'Name': 'example.ts.net'},
                  'Self': {'HostName': 'desk', 'UserID': 1},
                  'Peer': {
                      'b': {'HostName': 'zeta', 'Online': True, 'Active': True, 'CurAddr': '1.2.3.4:41641',
                            'TailscaleIPs': ['100.64.0.2'], 'UserID': 1, 'TaildropTarget': 1, 'OS': 'linux'},
                      'a': {'HostName': 'alpha', 'Online': False, 'TailscaleIPs': ['100.64.0.3'],
                            'UserID': 1, 'TaildropTarget': 5, 'OS': 'macOS'},
                      'c': {'DNSName': 'shared.example.ts.net.', 'Online': True, 'Active': True, 'Relay': 'fra',
                            'TailscaleIPs': ['100.64.0.4'], 'UserID': 2, 'OS': 'android'}}}
        summary = self.status.summarize(sample, 'person', 'person')
        self.assertEqual(summary['state'], 'connected')
        self.assertTrue(summary['operator'])
        self.assertEqual(summary['device'], 'desk')
        self.assertEqual(summary['addresses'], ['100.64.0.10', 'fd7a::10'])
        self.assertEqual([peer['name'] for peer in summary['peers']], ['shared', 'zeta', 'alpha'])
        self.assertEqual([peer['connection'] for peer in summary['peers']], ['relayed', 'direct', 'offline'])
        self.assertEqual([peer['taildrop'] for peer in summary['peers']], [False, True, False])

    def test_states_operator_and_hostile_text(self):
        summary = self.status.summarize({'BackendState': 'NeedsLogin', 'Self': None, 'Peer': None,
                                         'CurrentTailnet': None}, '', 'person')
        self.assertEqual((summary['state'], summary['operator'], summary['peers']), ('signed-out', False, []))
        self.assertIsNone(self.status.summarize({'BackendState': 'Stopped'}, None, 'person')['operator'])
        self.assertEqual(self.status.summarize({'BackendState': 'Odd'}, '', 'person')['state'], 'unavailable')
        peer = self.status.peer_entry({'HostName': 'bad\nname' + 'x' * 300, 'Online': True}, 1)
        self.assertEqual(peer['name'][:8], 'bad?name')
        self.assertEqual(len(peer['name']), 128)
        self.assertFalse(peer['taildrop'])

    def test_read_reports_missing_and_failing_tailscale_as_json_states(self):
        with patch.object(self.status.shutil, 'which', return_value=None):
            self.assertEqual(self.status.read()['state'], 'not-installed')
        with patch.object(self.status.shutil, 'which', return_value='/usr/bin/tailscale'), \
             patch.object(self.status.subprocess, 'run', return_value=Mock(returncode=1, stdout='')):
            self.assertEqual(self.status.read()['state'], 'unavailable')
        replies = [Mock(returncode=0, stdout=json.dumps({'BackendState': 'Stopped'})),
                   Mock(returncode=0, stdout=json.dumps({'OperatorUser': 'person'}))]
        with patch.object(self.status.shutil, 'which', return_value='/usr/bin/tailscale'), \
             patch.object(self.status.subprocess, 'run', side_effect=replies) as command, \
             patch.object(self.status.getpass, 'getuser', return_value='person'):
            result = self.status.read()
        self.assertEqual((result['state'], result['operator']), ('disconnected', True))
        self.assertTrue(all(call.kwargs['timeout'] <= 3 for call in command.call_args_list))

    def test_peer_list_stays_bounded(self):
        peers = {str(index): {'HostName': 'peer' + str(index), 'TailscaleIPs': ['100.64.0.1']} for index in range(500)}
        summary = self.status.summarize({'BackendState': 'Running', 'Peer': peers}, '', 'person')
        self.assertEqual(len(summary['peers']), self.status.PEER_LIMIT)
        self.assertEqual(summary['peerCount'], 500)
        self.assertLess(len(json.dumps(summary)), 64 * 1024)


class ManifestTests(unittest.TestCase):
    def test_manifests_and_review_snapshot(self):
        import eitr_plugin_manifest
        import eitr_plugin_review
        # Plugins with QML panels are larger than the local assistant's 24 KiB context, so their
        # review goes through the Claude transport, as an installer with Claude would.
        for identifier, transport in (('wireguard', 'claude'), ('networkmanager-vpn', 'claude'), ('tailscale', 'claude'), ('ollama', 'claude')):
            folder = ROOT / 'plugins' / identifier
            self.assertEqual(eitr_plugin_manifest.manifest(folder)['id'], identifier)
            with tempfile.TemporaryDirectory() as temporary:
                records = eitr_plugin_review.snapshot(folder, Path(temporary) / 'repository')
                prompt = eitr_plugin_review.prompt(records, '.')
                self.assertIn('action.py', prompt)
                self.assertIn('eitr-plugin.json', prompt)
            answer = 'Offline review transport verified.'
            with patch.object(eitr_plugin_review, 'selected_assistant', return_value=transport), \
                 patch.object(eitr_plugin_review.eitr_local_assistant, 'ask', return_value=answer) as local_assistant, \
                 patch.object(eitr_plugin_review, 'ask_claude', return_value=answer) as claude_assistant:
                assistant = local_assistant if transport == 'local' else claude_assistant
                result = eitr_plugin_review.check(folder)
                self.assertIn('Offline review transport verified.', result)
                self.assertIn('action.py', assistant.call_args.args[0])
        self.assertEqual(len(eitr_plugin_manifest.repository_plugins(ROOT)), 10)

    def test_notes_and_visualizer_manifests_limits_and_review(self):
        import eitr_plugin_install
        import eitr_plugin_manifest
        import eitr_plugin_review

        notes = eitr_plugin_manifest.manifest(ROOT / 'plugins/notes')
        self.assertEqual(notes['schemaVersion'], 2)
        self.assertEqual(notes['id'], 'notes')
        self.assertEqual(notes.get('capabilities', []), [])
        note_widget, = notes['ui']['widgets']
        self.assertEqual((note_widget['id'], note_widget['surface']), ('note', 'none'))
        self.assertEqual((note_widget['defaultWidth'], note_widget['defaultHeight']), (260, 240))
        self.assertEqual(eitr_plugin_install.live_flags(notes), [])

        for plugin_id in ('notes', 'visualizer'):
            folder = ROOT / 'plugins' / plugin_id
            with tempfile.TemporaryDirectory() as temporary:
                records = eitr_plugin_review.snapshot(folder, Path(temporary) / 'repository')
                prompt = eitr_plugin_review.prompt(records, '.')
                self.assertIn('eitr-plugin.json', prompt)
            for source_file in (*folder.glob('*.qml'), *folder.glob('*.js')):
                self.assertLessEqual(len(source_file.read_text().splitlines()), 400, source_file.name)

        visualizer = eitr_plugin_manifest.manifest(ROOT / 'plugins/visualizer')
        self.assertEqual(visualizer['schemaVersion'], 2)
        self.assertEqual(visualizer['id'], 'visualizer')
        self.assertEqual(visualizer['version'], '0.3.1')
        self.assertEqual(visualizer['capabilities'], ['audio-spectrum'])
        vis_widget, = visualizer['ui']['widgets']
        self.assertEqual((vis_widget['id'], vis_widget['surface']), ('visualizer', 'none'))
        self.assertEqual((vis_widget['defaultWidth'], vis_widget['defaultHeight']), (900, 180))
        self.assertEqual((vis_widget['minWidth'], vis_widget['minHeight']), (120, 40))

    def test_vpn_plugins_declare_bar_items_panels_and_bounded_qml(self):
        import eitr_plugin_manifest
        for identifier in ('wireguard', 'networkmanager-vpn', 'tailscale'):
            manifest = eitr_plugin_manifest.manifest(ROOT / 'plugins' / identifier)
            self.assertEqual(manifest['schemaVersion'], 2)
            item, = manifest['ui']['barItems']
            panel, = manifest['ui']['panels']
            self.assertEqual(item['panel'], panel['id'])
            self.assertEqual((panel['surface'], panel['header']), ('panel', False))
            for entry in (item, panel):
                self.assertEqual(entry['dataCommand'], {'run': 'status.py', 'arguments': ['--json']})
                self.assertGreaterEqual(entry['refreshInterval'], 5000)
            for qml in (ROOT / 'plugins' / identifier).glob('*.qml'):
                self.assertLessEqual(len(qml.read_text().splitlines()), 400, qml.name)
        tailscale = eitr_plugin_manifest.manifest(ROOT / 'plugins/tailscale')
        self.assertEqual(tailscale['service'], {'run': 'receive.py'})


class WidgetRenderAndHostTests(unittest.TestCase):
    def test_js_helpers_if_node_available(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not available')
        result = subprocess.run(
            [node, str(ROOT / 'tests/test_widget_helpers.js')],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_offscreen_widget_renders(self):
        if not shutil.which('quickshell'):
            self.skipTest('quickshell not available')
        sys.path.insert(0, str(ROOT / 'tests'))
        import render_widgets
        with tempfile.TemporaryDirectory() as tmp:
            scenes = render_widgets.default_scenes(tmp)
            for scene in scenes:
                out = render_widgets.render_scene(scene)
                header = out.read_bytes()[:8]
                self.assertEqual(header, b'\x89PNG\r\n\x1a\n', scene['name'])

            vis_scenes = render_widgets.visualizer_scenes(tmp)
            vis_outputs = render_widgets.render_scenes_batch(vis_scenes)
            self.assertEqual(len(vis_outputs), 20)
            for out in vis_outputs:
                self.assertEqual(out.read_bytes()[:8], b'\x89PNG\r\n\x1a\n', out.name)
            from PIL import Image
            with Image.open(Path(tmp) / 'visualizer-ring-wide-dark.png') as ring_wide:
                self.assertEqual((ring_wide.width, ring_wide.height), (948, 228))
                pixels = ring_wide.convert('RGB').load()
                # Far left and far right outside the centred square must remain pure backdrop.
                for y in range(24, ring_wide.height - 24, 12):
                    self.assertEqual(pixels[48, y], pixels[8, y])
                    self.assertEqual(pixels[ring_wide.width - 49, y], pixels[8, y])
                # Inside the centred ring radius there must be rendered accent pixels.
                center_x, center_y = ring_wide.width // 2, ring_wide.height // 2
                ring_diffs = sum(
                    1 for dx in range(-75, 76, 3) for dy in range(-75, 76, 3)
                    if pixels[center_x + dx, center_y + dy] != pixels[8, center_y + dy]
                )
                self.assertGreater(ring_diffs, 20)

    def test_widget_contract_menus_persistence_and_escape(self):
        quickshell = shutil.which('quickshell')
        if not quickshell:
            self.skipTest('quickshell not available')
        sys.path.insert(0, str(ROOT / 'tests'))
        import render_widgets
        secret_note = 'Private note text should stay out of logs'
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            harness = tmp_path / 'contract_harness.qml'
            notes_uri = render_widgets.NOTES_QML.as_uri()
            harness.write_text(f"""import QtQuick
import QtQuick.Window
import Quickshell

ShellRoot {{
    Window {{
        width: 520
        height: 320
        visible: true

        QtObject {{
            id: notesApi
            property string pluginId: "notes"
            property string entryId: "note"
            property string instance: "note-a"
            property string surface: "none"
            property string title: "Note"
            property string detail: ""
            property bool compact: false
            property bool editing: false
            property bool acceptsKeyboard: false
            property bool keyboardFocus: false
            property color background: "#161821"
            property color foreground: "#ebeef5"
            property color accent: "#d5b55c"
            property var palette: ({{ surface: "#1c1f2b" }})
            property real radius: 12
            property real spacing: 8
            property string fontFamily: "sans-serif"
            property real headingSize: 16
            property real bodySize: 13
            property real captionSize: 11
            property var instanceData: ({{ version: 1, text: "{secret_note}", color: "blue" }})
            property bool instanceDataReady: true
            property var savedPayloads: []
            property var menuEntries: []
            property int releasedCount: 0
            signal instanceDataLoaded()
            signal keyboardReleased()
            signal menuTriggered(string id)
            function setMenu(entries) {{ menuEntries = entries || []; }}
            function saveInstanceData(value) {{
                const copy = savedPayloads.slice();
                copy.push(value);
                savedPayloads = copy;
            }}
            function releaseKeyboard() {{
                releasedCount += 1;
                keyboardFocus = false;
                keyboardReleased();
            }}
        }}

        Loader {{
            id: notesLoader
            width: 260
            height: 240
            Component.onCompleted: setSource("{notes_uri}", {{ api: notesApi }})
        }}

        Timer {{
            interval: 120
            running: true
            repeat: false
            onTriggered: {{
                notesApi.menuTriggered("green");
                notesApi.releaseKeyboard();
                const noteMenuIds = notesApi.menuEntries.map(entry => entry.id).join(",");
                console.log("CHECK:" + JSON.stringify({{
                    noteLoaded: notesLoader.status === Loader.Ready,
                    noteAcceptsKeyboard: notesApi.acceptsKeyboard,
                    noteReleased: notesApi.releasedCount,
                    noteMenuIds: noteMenuIds,
                    noteSavedColor: notesApi.savedPayloads.length > 0 ? notesApi.savedPayloads[notesApi.savedPayloads.length - 1].color : "",
                    noteTextMatched: notesApi.savedPayloads.length > 0 && notesApi.savedPayloads[notesApi.savedPayloads.length - 1].text === "{secret_note}"
                }}));
                Qt.quit();
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
                [quickshell, '-p', str(harness), '--no-duplicate'],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            combined = result.stdout + '\n' + result.stderr
            self.assertNotIn(secret_note, combined)
            marker = [line for line in combined.splitlines() if 'CHECK:' in line]
            self.assertTrue(marker, combined)
            payload = json.loads(marker[-1].split('CHECK:', 1)[1])
            self.assertTrue(payload['noteLoaded'])
            self.assertTrue(payload['noteAcceptsKeyboard'])
            self.assertEqual(payload['noteReleased'], 1)
            self.assertEqual(payload['noteMenuIds'], 'yellow,green,blue,pink,purple,theme')
            self.assertEqual(payload['noteSavedColor'], 'green')
            self.assertTrue(payload['noteTextMatched'])

    def test_visualizer_options_migration_fallback_and_menu(self):
        quickshell = shutil.which('quickshell')
        if not quickshell:
            self.skipTest('quickshell not available')
        sys.path.insert(0, str(ROOT / 'tests'))
        import render_widgets
        vis_uri = render_widgets.VISUALIZER_QML.as_uri()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_dir = tmp_path / 'config/eitr-plugin-visualizer'
            config_dir.mkdir(parents=True, exist_ok=True)
            options_file = config_dir / 'options.json'
            options_file.write_text('{"version":1,"style":"terminal","colors":"palette"}\n', encoding='utf-8')
            unknown_dir = tmp_path / 'config-unknown/eitr-plugin-visualizer'
            unknown_dir.mkdir(parents=True, exist_ok=True)
            (unknown_dir / 'options.json').write_text('{"version":1,"style":"mystery","colors":"unknown"}\n', encoding='utf-8')
            wave_dir = tmp_path / 'config-wave/eitr-plugin-visualizer'
            wave_dir.mkdir(parents=True, exist_ok=True)
            (wave_dir / 'options.json').write_text('{"version":1,"style":"wave","colors":"accent"}\n', encoding='utf-8')
            harness = tmp_path / 'visualizer_contract.qml'
            harness.write_text(f"""import QtQuick
import QtQuick.Window
import Quickshell

ShellRoot {{
    Window {{
        width: 320
        height: 200
        visible: true

        QtObject {{
            id: visApi
            property color background: "#161821"
            property color foreground: "#ebeef5"
            property color accent: "#d5b55c"
            property var palette: ({{
                color1: "#e06c75",
                color3: "#e5c07b",
                color4: "#61afef",
                color5: "#c678dd"
            }})
            property int spectrumBars: 64
            property int spectrumFrameRate: 30
            property bool spectrumSmoothing: false
            property var spectrum: [0.6, 0.7, 0.8, 0.5]
            property bool audioActive: true
            property var menuEntries: []
            signal menuTriggered(string id)
            function setMenu(entries) {{ menuEntries = entries || []; }}
        }}

        Loader {{
            id: visLoader
            width: 240
            height: 180
            Component.onCompleted: setSource("{vis_uri}", {{ api: visApi }})
        }}

        Timer {{
            id: stepTimer
            interval: 90
            running: true
            repeat: true
            property int step: 0
            onTriggered: {{
                if (step === 0) {{
                    const initialStyle = visLoader.item.activeStyle;
                    const initialColors = visLoader.item.activeColors;
                    const menuIds = visApi.menuEntries.map(function(entry) {{ return entry.id; }}).join(",");
                    visApi.menuTriggered("ring");
                    visApi.menuTriggered("accent");
                    console.log("VIS_STEP0:" + JSON.stringify({{
                        initialStyle: initialStyle,
                        initialColors: initialColors,
                        menuIds: menuIds,
                        afterRingStyle: visLoader.item.activeStyle,
                        afterAccentColors: visLoader.item.activeColors,
                        checkedAfter: visApi.menuEntries.filter(function(entry) {{ return entry.checked; }}).map(function(entry) {{ return entry.id; }}).join(",")
                    }}));
                    step = 1;
                    return;
                }}
                Qt.quit();
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
            env['LANG'] = 'en_US.UTF-8'
            for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_RUNTIME_DIR'):
                Path(env[key]).mkdir(parents=True, exist_ok=True)
            os.chmod(env['XDG_RUNTIME_DIR'], 0o700)
            result = subprocess.run(
                [quickshell, '-p', str(harness), '--no-duplicate'],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            combined = result.stdout + '\n' + result.stderr
            marker = [line for line in combined.splitlines() if 'VIS_STEP0:' in line]
            self.assertTrue(marker, combined)
            payload = json.loads(marker[-1].split('VIS_STEP0:', 1)[1])
            self.assertEqual(payload['initialStyle'], 'bars')
            self.assertEqual(payload['initialColors'], 'palette')
            self.assertEqual(payload['menuIds'], 'wave,bars,ring,mirror,dots,accent,palette')
            self.assertEqual(payload['afterRingStyle'], 'ring')
            self.assertEqual(payload['afterAccentColors'], 'accent')
            # The widget menu highlights the new choice right away, not the one before it.
            self.assertEqual(payload['checkedAfter'], 'ring,accent')
            saved_disk = json.loads(options_file.read_text(encoding='utf-8'))
            self.assertEqual(saved_disk, {'version': 1, 'style': 'ring', 'colors': 'accent'})

            for cfg_path, expected_style in ((unknown_dir.parent, 'bars'), (wave_dir.parent, 'wave')):
                env_case = env.copy()
                env_case['XDG_CONFIG_HOME'] = str(cfg_path)
                res_case = subprocess.run(
                    [quickshell, '-p', str(harness), '--no-duplicate'],
                    env=env_case,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(res_case.returncode, 0, res_case.stderr + res_case.stdout)
                case_lines = [line for line in (res_case.stdout + '\n' + res_case.stderr).splitlines() if 'VIS_STEP0:' in line]
                self.assertTrue(case_lines)
                case_payload = json.loads(case_lines[-1].split('VIS_STEP0:', 1)[1])
                self.assertEqual(case_payload['initialStyle'], expected_style)


if __name__ == '__main__':
    unittest.main()
