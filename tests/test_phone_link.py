"""Offline contract tests; no session bus, phone, service or clipboard is used."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/phone-link'
sys.path.insert(0, str(ROOT.parent / 'eitr/distro/lib'))


def load(name):
    with patch.object(sys, 'path', [str(PLUGIN), *sys.path]):
        spec = importlib.util.spec_from_file_location('phone_' + name, PLUGIN / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class PhoneStatusTests(unittest.TestCase):
    def setUp(self):
        self.status = load('status')
        self.bus = Mock()
        self.bus.running.return_value = True

    def test_missing_and_stopped_do_not_activate_daemon(self):
        with patch.object(self.status.shutil, 'which', return_value=None):
            self.assertEqual(self.status.read(self.bus)['state'], 'missing')
        self.bus.running.assert_not_called()
        self.bus.running.return_value = False
        with patch.object(self.status.shutil, 'which', return_value='/fake/kdeconnect-cli'):
            self.assertEqual(self.status.read(self.bus)['state'], 'stopped')
        self.bus.call.assert_not_called()

    def test_battery_incoming_and_unsupported_features(self):
        self.bus.properties.side_effect = [
            {'name': '<b>Phone</b>\n', 'type': 'phone', 'isReachable': True, 'isPaired': True},
            {'charge': 80, 'isCharging': True, 'hasBattery': True}]
        self.bus.call.return_value = (['kdeconnect_battery', 'kdeconnect_share', 'kdeconnect_arbitrary'],)
        result = self.status.device_entry(self.bus, 'phone_1')
        self.assertEqual((result['battery'], result['charging']), (80, True))
        self.assertEqual(result['name'], '<b>Phone</b> ')
        self.assertEqual(result['plugins'], ['kdeconnect_share'])
        self.bus.properties.side_effect = None
        self.bus.properties.return_value = {'name': 'Tablet', 'isPairRequestedByPeer': True, 'verificationKey': '123456'}
        result = self.status.device_entry(self.bus, 'tablet')
        self.assertTrue(result['incoming'])
        self.assertEqual(result['verification'], '123456')
        self.assertIsNone(result['battery'])

    def test_invalid_battery_is_unknown(self):
        for charge in (-1, 101, True, '90', None):
            with self.subTest(charge=charge):
                self.bus.properties.side_effect = [
                    {'name': 'Phone', 'isReachable': True, 'isPaired': True}, {'charge': charge}]
                self.bus.call.return_value = (['kdeconnect_battery'],)
                self.assertIsNone(self.status.device_entry(self.bus, 'phone')['battery'])

    def test_incoming_and_connected_devices_take_priority_and_reads_are_bounded(self):
        self.bus.call.side_effect = [(list(map(str, range(100))),), (['99'],)]
        self.bus.properties.return_value = {'pairingRequests': ['98']}
        def device(_connection, identifier):
            return dict(id=identifier, incoming=identifier == '98', paired=True, reachable=True, name=identifier)
        with patch.object(self.status.shutil, 'which', return_value='/fake/cli'), \
             patch.object(self.status, 'device_entry', side_effect=device) as entry:
            result = self.status.read(self.bus)
        self.assertEqual(result['total'], 100)
        self.assertEqual(result['devices'][0]['id'], '98')
        self.assertIn('99', [device['id'] for device in result['devices']])
        self.assertEqual(entry.call_count, self.status.DEVICE_LIMIT)

    def test_disappearing_device_and_bus_failure(self):
        self.bus.call.side_effect = [(['gone'],), ([],)]
        self.bus.properties.return_value = {}
        with patch.object(self.status.shutil, 'which', return_value='/fake/cli'), \
             patch.object(self.status, 'device_entry', side_effect=TimeoutError):
            result = self.status.snapshot(self.bus)
        self.assertTrue(result['partial'])
        self.assertEqual(result['devices'], [])
        self.bus.running.side_effect = TimeoutError
        with patch.object(self.status.shutil, 'which', return_value='/fake/cli'):
            self.assertEqual(self.status.snapshot(self.bus)['state'], 'unavailable')

    def test_stream_json_fits_host_utf8_limit_without_splitting_devices(self):
        state = dict(state='ready', total=8, devices=[{'name': '龍' * 64, 'data': 'x' * 400} for _ in range(8)])
        encoded = self.status.encode(state)
        self.assertLessEqual(len(encoded.encode('utf-8')), 4000)
        parsed = json.loads(encoded)
        self.assertLess(len(parsed['devices']), 8)
        self.assertEqual(parsed['total'], 8)
        self.assertEqual(len(state['devices']), 8)

    def test_watcher_subscribes_before_snapshot_and_coalesces_signals(self):
        connection = Mock()
        loop = Mock()
        callbacks = []
        def subscribe(*arguments):
            callbacks.append(arguments[-1])
            return len(callbacks)
        connection.bus.signal_subscribe.side_effect = subscribe
        def run_loop():
            changed = callbacks[0]
            changed(None, None, '/modules/kdeconnect/devices/phone/battery', 'battery', 'refreshed', None)
            changed(None, None, '/modules/kdeconnect/devices/phone', 'device', 'pairStateChanged', None)
        loop.run.side_effect = run_loop
        with patch.object(self.status, 'Connection', return_value=connection), \
             patch.object(self.status.GLib, 'MainLoop', return_value=loop), \
             patch.object(self.status.GLib, 'timeout_add', return_value=42) as timer, \
             patch.object(self.status.GLib, 'source_remove') as remove, \
             patch.object(self.status, 'snapshot', return_value=dict(state='stopped', devices=[], total=0)) as snapshot, \
             patch('builtins.print'):
            self.status.watch()
        self.assertEqual(len(callbacks), 2)
        snapshot.assert_called_once()
        timer.assert_called_once()
        remove.assert_called_once_with(42)
        self.assertEqual(connection.bus.signal_unsubscribe.call_count, 2)


class PhoneActionTests(unittest.TestCase):
    def setUp(self):
        self.action = load('action')
        self.bus = Mock()
        self.bus.running.return_value = True
        self.bus.properties.return_value = {'isReachable': True, 'isPaired': True, 'isPairRequestedByPeer': True}
        self.bus.call.return_value = (list(self.action.PLUGINS.values()),)

    def test_invalid_identifier_and_action_cannot_reach_commands(self):
        for action, identifier in [('ping', '--help'), ('ping', 'bad/path'), ('shell', 'phone')]:
            with patch.object(self.action, 'run') as command:
                with self.assertRaises(ValueError):
                    self.action.perform(action, identifier, connection=self.bus)
                command.assert_not_called()
        self.bus.call.assert_not_called()

    def test_unpair_requires_explicit_confirmation(self):
        with patch.object(self.action, 'run') as command:
            for payload in (None, {}, {'confirmed': False}, {'confirmed': 1}):
                with self.assertRaises(ValueError):
                    self.action.perform('unpair', 'phone', payload, self.bus)
            command.assert_not_called()
            self.action.perform('unpair', 'phone', {'confirmed': True}, self.bus)
        command.assert_called_once_with(['kdeconnect-cli', '-d', 'phone', '--unpair'])

    def test_accept_reject_and_expired_request(self):
        for action, method in [('accept', 'acceptPairing'), ('reject', 'cancelPairing')]:
            self.action.perform(action, 'phone', connection=self.bus)
            self.assertEqual(self.bus.call.call_args.args[2], method)
        self.bus.properties.return_value = {}
        with self.assertRaises(RuntimeError):
            self.action.perform('accept', 'phone', connection=self.bus)

    def test_offline_unpaired_and_unsupported_actions_refused(self):
        for props, plugins in [({}, []), ({'isReachable': True}, []),
                               ({'isReachable': True, 'isPaired': True}, [])]:
            self.bus.properties.return_value = props
            self.bus.call.return_value = (plugins,)
            with patch.object(self.action, 'run') as command:
                with self.assertRaises(RuntimeError):
                    self.action.perform('ring', 'phone', connection=self.bus)
                command.assert_not_called()

    def test_clipboard_is_sent_over_dbus_never_argv(self):
        text = 'secret\n$(not a command)'
        with patch.object(self.action, 'run') as command:
            self.action.perform('clipboard', 'phone', {'text': text}, self.bus)
        command.assert_not_called()
        self.assertEqual(self.bus.call.call_args.args, ('/modules/kdeconnect/devices/phone/share',
                         'org.kde.kdeconnect.device.share', 'shareText', '(s)', (text,)))
        with self.assertRaises(ValueError):
            self.action.perform('clipboard', 'phone', {'text': ''}, self.bus)

    def test_pair_ping_and_ring_use_fixed_cli_arguments(self):
        with patch.object(self.action, 'run') as command:
            self.action.perform('ping', 'phone', connection=self.bus)
            command.assert_called_with(['kdeconnect-cli', '-d', 'phone', '--ping'])
            self.action.perform('ring', 'phone', connection=self.bus)
            command.assert_called_with(['kdeconnect-cli', '-d', 'phone', '--ring'])
            self.bus.properties.return_value = {'isReachable': True, 'isPaired': False}
            self.action.perform('pair', 'phone', connection=self.bus)
            command.assert_called_with(['kdeconnect-cli', '-d', 'phone', '--pair'])

    def test_send_file_uri_preserves_spaces_and_leading_dash_and_cancellation(self):
        import tempfile
        portal = types.ModuleType('portal')
        portal.choose_files = Mock()
        with tempfile.TemporaryDirectory() as temporary:
            files = [Path(temporary) / 'a b.txt', Path(temporary) / '-name.txt']
            for filename in files:
                filename.write_text('fixture')
            portal.choose_files.return_value = files
            with patch.dict(sys.modules, {'portal': portal}), \
                 patch.object(self.action, 'Connection', return_value=self.bus), \
                 patch.object(self.action, 'run') as command:
                self.action.perform('send', 'phone', connection=self.bus)
                command.assert_called_once_with(['kdeconnect-cli', '-d', 'phone', '--share',
                                                 *[filename.as_uri() for filename in files]], timeout=10)
                command.reset_mock()
                portal.choose_files.return_value = []
                self.assertEqual(self.action.perform('send', 'phone', connection=self.bus), 'cancelled')
                command.assert_not_called()

    def test_browse_opens_only_a_valid_mounted_directory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            self.bus.call.side_effect = [(['kdeconnect_sftp'],), (True,), (temporary,)]
            with patch.object(self.action, 'run') as command:
                self.action.perform('browse', 'phone', connection=self.bus)
            command.assert_called_once_with(['xdg-open', Path(temporary).as_uri()])
        self.bus.call.side_effect = [(['kdeconnect_sftp'],), (False,)]
        with patch.object(self.action, 'run') as command:
            with self.assertRaises(RuntimeError):
                self.action.perform('browse', 'phone', connection=self.bus)
            command.assert_not_called()

    def test_start_prefers_package_user_service_and_falls_back_to_detached_daemon(self):
        self.bus.running.return_value = False
        with patch.object(self.action, 'Connection', return_value=self.bus), \
             patch.object(self.action.Path, 'glob', return_value=[Path('/usr/lib/systemd/user/kdeconnect.service')]), \
             patch.object(self.action, 'run') as command:
            self.action.start()
            command.assert_called_once_with(['systemctl', '--user', 'start', 'kdeconnect.service'])
        with patch.object(self.action, 'Connection', return_value=self.bus), \
             patch.object(self.action.Path, 'glob', return_value=[]), \
             patch.object(self.action.shutil, 'which', return_value='/fake/kdeconnectd'), \
             patch.object(self.action.subprocess, 'Popen') as spawn:
            self.action.start()
        self.assertTrue(spawn.call_args.kwargs['start_new_session'])
        self.assertEqual(spawn.call_args.args[0], ['/fake/kdeconnectd'])

    def test_failures_do_not_echo_private_stderr(self):
        with patch.object(self.action.subprocess, 'run', return_value=Mock(returncode=1, stderr=b'private')):
            with self.assertRaisesRegex(RuntimeError, '^command-failed$'):
                self.action.run(['kdeconnect-cli'])
        with patch.object(self.action.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake', 8)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.action.run(['kdeconnect-cli'])


class PhoneManifestTests(unittest.TestCase):
    def test_manifest_streams_packages_and_review(self):
        import eitr_plugin_manifest
        import eitr_plugin_review
        import tempfile
        manifest = eitr_plugin_manifest.manifest(PLUGIN)
        self.assertEqual(manifest['packages'], ['kdeconnect', 'python-gobject'])
        item, = manifest['ui']['barItems']
        panel, = manifest['ui']['panels']
        self.assertEqual(item['panel'], panel['id'])
        self.assertEqual(panel['width'], 420)
        self.assertEqual(panel['maxHeight'], 640)
        for entry in (item, panel):
            self.assertEqual(entry['dataStream'], {'run': 'status.py', 'arguments': ['--watch']})
            self.assertEqual(entry['refreshInterval'], 0)
        with tempfile.TemporaryDirectory() as temporary:
            records = eitr_plugin_review.snapshot(PLUGIN, Path(temporary) / 'review')
            prompt = eitr_plugin_review.prompt(records, '.')
        self.assertIn('PhonePanel.qml', prompt)
        self.assertIn('action.py', prompt)
        for source in PLUGIN.iterdir():
            if source.suffix in ('.qml', '.py', '.js'):
                self.assertLessEqual(len(source.read_text().splitlines()), 400, source.name)


class PhoneConnectionTests(unittest.TestCase):
    def test_no_auto_start_and_remaining_deadline(self):
        connection = load('connection')
        bus = Mock()
        bus.call_sync.return_value = connection.GLib.Variant('(b)', (False,))
        with patch.object(connection.Gio, 'bus_get_sync', return_value=bus), \
             patch.object(connection.time, 'monotonic', side_effect=[10, 10.25, 17]):
            client = connection.Connection()
            self.assertFalse(client.running())
            arguments = bus.call_sync.call_args.args
            self.assertEqual(arguments[0], 'org.freedesktop.DBus')
            self.assertEqual(arguments[6], connection.Gio.DBusCallFlags.NO_AUTO_START)
            self.assertLessEqual(arguments[7], 1000)
            with self.assertRaises(TimeoutError):
                client.running()
        self.assertEqual(bus.call_sync.call_count, 1)


class PhonePortalTests(unittest.TestCase):
    def test_selection_cancellation_remote_uri_and_timeout_without_a_bus(self):
        from gi.repository import Gio, GLib
        portal = load('portal')
        handle = '/org/freedesktop/portal/desktop/request/1_2/eitr_phone_link_' + str(os.getpid())
        for code, uris, expired in ((0, ['file:///tmp/a%20b.txt'], False), (1, [], False),
                                    (0, ['https://example.test/file'], False), (None, [], True)):
            with self.subTest(code=code, uris=uris, expired=expired):
                bus = Mock()
                bus.get_unique_name.return_value = ':1.2'
                loop = Mock()
                callbacks = {}
                def subscribe(*arguments):
                    callbacks['response'] = arguments[-1]
                    return 1
                def call(*_arguments):
                    if code is not None:
                        callbacks['response'](None, None, None, None, None,
                            GLib.Variant('(ua{sv})', (code, {'uris': GLib.Variant('as', uris)})))
                    return GLib.Variant('(o)', (handle,))
                def timer(_seconds, callback):
                    callbacks['timeout'] = callback
                    return 2
                bus.signal_subscribe.side_effect = subscribe
                bus.call_sync.side_effect = call
                loop.run.side_effect = lambda: callbacks['timeout']()
                with patch.object(Gio, 'bus_get_sync', return_value=bus), \
                     patch.object(GLib, 'MainLoop', return_value=loop), \
                     patch.object(GLib, 'timeout_add_seconds', side_effect=timer), \
                     patch.object(GLib, 'source_remove') as remove:
                    if uris and not uris[0].startswith('file:'):
                        with self.assertRaises(ValueError):
                            portal.choose_files('Fixture')
                    else:
                        self.assertEqual(portal.choose_files('Fixture'), [Path('/tmp/a b.txt')] if code == 0 else [])
                bus.signal_unsubscribe.assert_called_once_with(1)
                if expired:
                    self.assertEqual(bus.call_sync.call_args.args[3], 'Close')
                    remove.assert_not_called()
                else:
                    remove.assert_called_once_with(2)


@unittest.skipUnless(shutil.which('dbus-run-session'), 'Private D-Bus runner required')
class PhonePrivateBusTests(unittest.TestCase):
    def test_gio_properties_pairing_battery_owner_changes_and_portal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            environment = {**os.environ, 'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=/nonexistent',
                           'XDG_RUNTIME_DIR': temporary}
            result = subprocess.run(['dbus-run-session', '--', sys.executable,
                                     str(ROOT / 'tests/fixtures/phone_bus.py'), str(PLUGIN)],
                                    text=True, capture_output=True, timeout=25, env=environment)
        if 'Failed to bind socket' in result.stderr and 'Operation not permitted' in result.stderr:
            self.skipTest('Sandbox forbids binding the private D-Bus socket')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PHONE_PRIVATE_BUS_OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
