"""Radio Globe uses temporary XDG roots, fake HTTP and fake player commands."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/radio-globe'
DESKTOP = ROOT.parent / 'eitr'


def modules():
    loaded = {}
    with patch.dict(sys.modules), patch.object(sys, 'path', [str(PLUGIN), *sys.path]):
        for name in ('storage', 'browser', 'player', 'runtime'):
            spec = importlib.util.spec_from_file_location(name, PLUGIN / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            loaded[name] = module
    return loaded


def sample(**values):
    return dict(stationuuid='station-1', name='Radio Example', tags='jazz,ambient', codec='MP3',
                bitrate=128, lastcheckok=1, countrycode='BR', url='https://stream.example/live', **values)


class RadioTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        environment = {name: self.temporary.name for name in
                       ('HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_RUNTIME_DIR', 'XDG_STATE_HOME')}
        self.environment = patch.dict(os.environ, environment)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        loaded = modules()
        self.browser, self.player, self.runtime, self.storage = [loaded[name] for name in ('browser', 'player', 'runtime', 'storage')]

    def test_station_records_filter_protocols_broken_entries_and_hostile_text(self):
        for address in ('file:///etc/passwd', 'javascript:alert(1)', '--script=bad', 'https://user:pass@example.com',
                        'https://example.com/\nstream', 'https://[bad', 'https://example.com:invalid'):
            record = sample()
            record['url'] = address
            self.assertIsNone(self.browser.station(record), address)
        record = sample()
        record.update(name='<b>News</b>\n' + 'x' * 300, url_resolved='http://example.net/stream', bitrate=None)
        cleaned = self.browser.station(record)
        self.assertEqual(cleaned['url'], 'http://example.net/stream')
        self.assertLessEqual(len(cleaned['name']), 160)
        self.assertNotIn('\n', cleaned['name'])
        for malformed in (None, [], {}, {**sample(), 'lastcheckok': 0}):
            self.assertIsNone(self.browser.station(malformed))

    def test_discovery_uses_documented_dns_randomization_and_reverse_names(self):
        entries = [(socket.AF_INET, socket.SOCK_STREAM, 0, '', ('1.2.3.4', 443)),
                   (socket.AF_INET, socket.SOCK_STREAM, 0, '', ('2.3.4.5', 443))]
        with patch.object(self.browser.socket, 'getaddrinfo', return_value=entries) as lookup, \
             patch.object(self.browser.socket, 'gethostbyaddr', side_effect=[('de1.api.radio-browser.info', [], []), ('host.attacker.test', [], [])]), \
             patch.object(self.browser.random, 'shuffle') as shuffle:
            self.assertEqual(self.browser.servers(), ['https://de1.api.radio-browser.info'])
        self.assertEqual(lookup.call_args.args[:2], ('all.api.radio-browser.info', 443))
        shuffle.assert_called_once()

    def test_failover_and_deadline_are_not_swallowed(self):
        with patch.object(self.browser, 'servers', return_value=['https://a', 'https://b']), \
             patch.object(self.browser, 'json_request', side_effect=[OSError('offline'), []]) as request:
            self.assertEqual(self.browser.request('/json/countries'), [])
            self.assertEqual(request.call_count, 2)
        with patch.object(self.browser, 'servers', side_effect=lambda: self.browser.deadline(None, None)):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                self.browser.request('/json/countries')
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))

    def test_http_uses_agent_size_bound_and_timeout(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'[]'
        with patch.object(self.browser, 'urlopen', return_value=response) as opener:
            self.assertEqual(self.browser.json_request('https://example.test/json/countries'), [])
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'), 'EitrRadioGlobe/1.0')
        self.assertLessEqual(opener.call_args.kwargs['timeout'], 3)
        response.read.return_value = b' ' * (2 * 1024 * 1024 + 1)
        with patch.object(self.browser, 'urlopen', return_value=response), self.assertRaisesRegex(ValueError, 'too large'):
            self.browser.json_request('https://example.test')

    def test_real_alarm_interrupts_a_hanging_dns_lookup(self):
        original = signal.setitimer
        def schedule(kind, duration, *values):
            return original(kind, 0.05 if duration == 7.0 else duration, *values)
        started = time.monotonic()
        with patch.object(self.browser, 'servers', side_effect=lambda: time.sleep(2)), \
             patch.object(self.browser.signal, 'setitimer', side_effect=schedule):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                self.browser.request('/json/countries')
        self.assertLess(time.monotonic() - started, 1)

    def test_ipc_skips_events_and_correlates_command_reply(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.recv.side_effect = [b'{"event":"start-file"}\n', b'{"request_id":1,"error":"success","data":1234}\n']
        with patch.object(self.player.socket, 'socket', return_value=connection):
            self.assertEqual(self.player.ipc(['get_property', 'pid']), 1234)
        payload = json.loads(connection.sendall.call_args.args[0])
        self.assertEqual(payload, {'command': ['get_property', 'pid'], 'request_id': 1})
        self.assertTrue(connection.connect.call_args.args[0].endswith('/radio-globe/mpv.sock'))

    def test_only_private_player_socket_is_stopped(self):
        calls = []
        with patch.object(self.player, 'ipc', side_effect=lambda command: calls.append(command)), \
             patch.object(self.player.subprocess, 'run') as runner:
            self.player.stop()
        self.assertEqual(calls, [['quit']])
        runner.assert_not_called()

    def test_country_cache_is_one_day_and_offline_can_use_stale_data(self):
        records = [{'name': 'Brazil', 'iso_3166_1': 'BR', 'stationcount': '300'},
                   {'name': 'Broken', 'iso_3166_1': 'XX', 'stationcount': 'oops'}, None]
        with patch.object(self.browser, 'request', return_value=records) as request, patch.object(self.browser.time, 'time', return_value=100000):
            result = self.browser.countries()
            self.assertEqual(result['countries'][0]['location'], self.browser.LOCATIONS['BR'])
            self.assertFalse(result['stale'])
            self.browser.countries()
            request.assert_called_once_with('/json/countries', {'hidebroken': 'true'})
        with patch.object(self.browser.time, 'time', return_value=200000), \
             patch.object(self.browser, 'request', side_effect=RuntimeError('offline')):
            self.assertTrue(self.browser.countries()['stale'])
        (self.storage.folder('CACHE') / 'countries.json').unlink()
        with patch.object(self.browser, 'request', side_effect=RuntimeError('offline')), self.assertRaisesRegex(RuntimeError, 'offline'):
            self.browser.countries()

    def test_country_name_tag_queries_and_paging(self):
        broken = {**sample(), 'lastcheckok': 0}
        with patch.object(self.browser, 'request', return_value=[sample(), broken]) as request:
            result = self.browser.stations('country', 'BR', 50)
            self.assertEqual(len(result['stations']), 1)
            self.assertEqual(request.call_args.args[0], '/json/stations/bycountrycodeexact/BR')
            self.assertEqual(request.call_args.args[1]['offset'], 50)
            self.browser.stations('name', 'Jazz & Blues')
            self.assertEqual(request.call_args.args[1]['name'], 'Jazz & Blues')
            self.browser.stations('tag', 'ambient')
            self.assertEqual(request.call_args.args[1]['tag'], 'ambient')
        with patch.object(self.browser, 'request', return_value=[sample()] * 50):
            self.assertTrue(self.browser.stations('name', 'radio')['more'])

    def test_favorites_are_atomic_uuid_toggles(self):
        with patch.object(self.player, 'status', return_value=None):
            added = self.runtime.action('favorite', sample())
            self.assertEqual(added['favorites'][0]['stationuuid'], 'station-1')
            self.assertEqual(self.runtime.action('favorite', sample())['favorites'], [])
        self.assertEqual(list(self.storage.folder('CONFIG').glob('.radio-*')), [])
        self.assertEqual((self.storage.folder('CONFIG') / 'settings.json').stat().st_mode & 0o777, 0o600)

    def test_legacy_volume_is_ignored_and_not_saved_again(self):
        path = self.storage.folder('CONFIG') / 'settings.json'
        for old_value in (35, 'obsolete', None, {'unexpected': 'value'}):
            with self.subTest(old_value=old_value), patch.object(self.player, 'status', return_value=None), \
                 patch.object(self.player, 'play') as play:
                self.storage.write(path, dict(volume=old_value, favorites=[sample()]))
                self.assertEqual(self.runtime.settings(), {'favorites': [self.browser.station(sample())]})
                self.assertEqual(self.runtime.action('play', sample()),
                                 {'playing': None, 'favorites': [self.browser.station(sample())]})
                play.assert_called_once_with(sample())
                self.runtime.action('favorite', sample())
                self.assertEqual(self.storage.read(path, None), {'favorites': []})

    def test_volume_command_is_rejected(self):
        result = subprocess.run([sys.executable, str(PLUGIN / 'runtime.py'), 'volume', '35'],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        with self.assertRaisesRegex(ValueError, 'Unknown Radio Globe command'):
            self.runtime.action('volume', 35)

    def test_bar_status_has_no_network_or_favorites_payload(self):
        with patch.object(self.player, 'status', return_value=None), patch.object(self.browser, 'request') as request, \
             patch.object(self.runtime, 'settings') as settings:
            self.assertEqual(self.runtime.action('status'), {'playing': None})
            request.assert_not_called()
            settings.assert_not_called()

    def test_player_is_replaced_before_launch_and_url_stays_one_argument(self):
        record = sample()
        record['url'] = 'https://stream.example/live?a=1&b=$(bad)'
        process = Mock()
        process.poll.return_value = None
        with patch.object(self.player.shutil, 'which', return_value='/usr/bin/mpv'), \
             patch.object(self.player, 'stop') as stop, patch.object(self.player.subprocess, 'Popen', return_value=process) as launch, \
             patch.object(Path, 'exists', return_value=True), patch.object(Path, 'is_file', return_value=True):
            self.assertEqual(self.player.play(record), {'station': self.browser.station(record)})
        stop.assert_called_once()
        argv = launch.call_args_list[0].args[0]
        self.assertEqual(argv[-2:], ['--', record['url']])
        self.assertIn('--no-config', argv)
        self.assertIn('--load-scripts=no', argv)
        self.assertIn('--volume=100', argv)
        self.assertIn('--audio-client-name=Radio Globe', argv)
        self.assertFalse(any(argument.startswith('--script') for argument in argv))
        bridge = launch.call_args_list[1].args[0]
        self.assertTrue(bridge[1].endswith('/radio-globe/media.py'))
        self.assertEqual(bridge[3], self.browser.station(record)['name'])
        for call in launch.call_args_list:
            self.assertNotIn('shell', call.kwargs)

    def test_missing_player_fails_explicitly(self):
        with patch.object(self.player.shutil, 'which', return_value=None), self.assertRaisesRegex(RuntimeError, 'mpv'):
            self.player.play(sample())

    def test_player_status_reads_only_the_current_stream(self):
        record = self.browser.station(sample())
        self.storage.write(self.storage.folder('RUNTIME') / 'playing.json', record)
        with patch.object(self.player, 'ipc', return_value=record['url']) as ipc:
            self.assertEqual(self.player.status(), {'station': record})
        ipc.assert_called_once_with(['get_property', 'path'])

    def test_disappeared_player_never_claims_to_be_playing(self):
        self.storage.write(self.storage.folder('RUNTIME') / 'playing.json', sample())
        with patch.object(self.player, 'ipc', side_effect=ConnectionRefusedError):
            self.assertIsNone(self.player.status())
        with patch.object(self.player, 'ipc', side_effect=['https://different.example/live']):
            self.assertIsNone(self.player.status())

    def test_cli_offline_emits_json_under_temporary_xdg_roots(self):
        # Execute the real CLI but replace DNS at the import boundary in a child process.
        source = "import sys; sys.path.insert(0, sys.argv[1]); import browser, runtime; browser.servers=lambda: []; sys.argv=['runtime.py','countries']; sys.exit(runtime.main())"
        result = subprocess.run([sys.executable, '-c', source, str(PLUGIN)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertIn('connection', json.loads(result.stdout)['error'])

    def test_manifest_registration_and_review_are_valid(self):
        with patch.object(sys, 'path', [str(DESKTOP / 'distro/lib'), *sys.path]):
            import eitr_plugin_manifest
            import eitr_plugin_review
            manifest = eitr_plugin_manifest.manifest(PLUGIN)
            self.assertEqual(manifest['packages'], ['mpv', 'python-gobject'])
            self.assertNotIn('service', manifest)
            self.assertEqual(manifest['ui']['barItems'][0]['refreshInterval'], 30000)
            records = eitr_plugin_review.snapshot(PLUGIN, Path(self.temporary.name) / 'review')
            self.assertIn('RadioPanel.qml', eitr_plugin_review.prompt(records, '.'))
        for source in PLUGIN.glob('*'):
            if source.suffix in ('.py', '.qml', '.js'):
                self.assertLessEqual(len(source.read_text().splitlines()), 400, source.name)


if __name__ == '__main__':
    unittest.main()
