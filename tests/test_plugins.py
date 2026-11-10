"""Offline tests: no live networking, home writes or privileged commands."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent / 'eitr'
sys.path.insert(0, str(DESKTOP / 'distro/lib'))


def load(identifier, filename='action.py'):
    runtime = types.ModuleType('runtime')
    for name in ('choose', 'collect', 'launch', 'open_terminal', 'run', 'Step', 'wait_for_escape'):
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
        # Tailscale's QML panel is larger than the local assistant's 24 KiB context, so its
        # review goes through the Claude transport, as an installer with Claude would.
        for identifier, transport in (('tailscale', 'claude'),):
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
        self.assertEqual(len(eitr_plugin_manifest.repository_plugins(ROOT)), 3)

    def test_tailscale_declares_bar_item_panel_and_receiver_service(self):
        import eitr_plugin_manifest
        manifest = eitr_plugin_manifest.manifest(ROOT / 'plugins/tailscale')
        self.assertEqual(manifest['schemaVersion'], 2)
        item, = manifest['ui']['barItems']
        panel, = manifest['ui']['panels']
        self.assertEqual(item['panel'], panel['id'])
        self.assertEqual((panel['surface'], panel['header']), ('panel', False))
        for entry in (item, panel):
            self.assertEqual(entry['dataCommand'], {'run': 'status.py', 'arguments': ['--json']})
            self.assertGreaterEqual(entry['refreshInterval'], 5000)
        self.assertEqual(manifest['service'], {'run': 'receive.py'})
        for qml in (ROOT / 'plugins/tailscale').glob('*.qml'):
            self.assertLessEqual(len(qml.read_text().splitlines()), 400, qml.name)


if __name__ == '__main__':
    unittest.main()
