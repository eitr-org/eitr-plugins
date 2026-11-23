"""Ollama checks use fake services, streams and isolated state only."""
from contextlib import contextmanager
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/ollama'


def load(name):
    spec = importlib.util.spec_from_file_location('ollama_' + name, PLUGIN / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, 'path', [str(PLUGIN), *sys.path]):
        spec.loader.exec_module(module)
    return module


class OllamaTests(unittest.TestCase):
    def setUp(self):
        self.client = load('client')
        self.modules = patch.dict(sys.modules, {'client': self.client})
        ready = patch.object(self.client, 'ready', return_value=True)
        ready.start()
        self.addCleanup(ready.stop)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        environment = patch.dict(os.environ, {'XDG_STATE_HOME': self.temporary.name,
                                              'XDG_CONFIG_HOME': self.temporary.name})
        environment.start()
        self.addCleanup(environment.stop)

    def test_status_stopped_or_missing_never_contacts_api(self):
        status = load('status')
        for configured, running in ((False, False), (False, True), (True, False)):
            with self.subTest(configured=configured, running=running), \
                 patch.object(self.client, 'configured', return_value=configured), \
                 patch.object(self.client, 'active', return_value=running), \
                 patch.object(self.client, 'request') as request:
                self.assertFalse(status.read()['running'])
                request.assert_not_called()

    def test_partial_core_setup_opens_the_existing_setup_instead_of_listing_models(self):
        status = load('status')
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'ready', return_value=False), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(self.client, 'request') as request:
            result = status.read()
        self.assertFalse(result['ready'])
        request.assert_not_called()

    def test_bar_only_queries_loaded_models(self):
        status = load('status')
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(self.client, 'request', return_value={'models': [{'name': 'qwen3:4b', 'size': 500, 'size_vram': 300}]}) as request:
            result = status.read(bar=True)
            self.assertEqual((result['loaded'][0]['ram'], result['loaded'][0]['vram']), (200, 300))
            request.assert_called_once_with('ps')

    def test_snapshot_handles_older_api_and_partial_failure(self):
        status = load('status')
        self.assertNotIn('vram', status.models({'models': [{'name': 'model', 'size': 100}]}, loaded=True)[0])
        self.assertEqual(status.models({'models': [{'name': 'bad\nname', 'size': -1}]})[0]['size'], 0)
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(self.client, 'request', side_effect=[{'models': [{'name': 'model'}]}, ValueError('timed out')]):
            result = status.read()
        self.assertEqual(result['error'], 'timed out')
        self.assertEqual(result['loaded'][0]['name'], 'model')

    def test_transient_worker_is_detached_and_has_lifetime_limit(self):
        action = load('action')
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(action.subprocess, 'run', return_value=Mock(returncode=0)) as command:
            action.run(['pull', 'llama3.2:3b'])
        arguments = command.call_args.args[0]
        self.assertEqual(arguments[:3], ['systemd-run', '--user', '--collect'])
        self.assertIn('--property=RuntimeMaxSec=86400', arguments)
        self.assertEqual(arguments[-1], 'llama3.2:3b')
        self.assertEqual(command.call_args.kwargs['timeout'], 3)

    def test_unload_delete_and_cancel_use_exact_contracts(self):
        action = load('action')
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', side_effect=lambda unit=self.client.UNIT: unit == self.client.UNIT), \
             patch.object(self.client, 'request') as request, \
             patch.object(self.client, 'systemctl', return_value=Mock(returncode=0)) as systemctl:
            action.run(['unload', 'qwen3:4b'])
            request.assert_called_with('generate', {'model': 'qwen3:4b', 'keep_alive': 0, 'stream': False})
            action.run(['delete-confirmed', 'qwen3:4b'])
            request.assert_called_with('delete', {'model': 'qwen3:4b'}, method='DELETE')
            action.run(['cancel'])
            systemctl.assert_called_with('stop', self.client.PULL_UNIT, timeout=7)
            with self.assertRaises(ValueError):
                action.run(['delete', 'qwen3:4b'])

    def test_stop_and_delete_refuse_during_download(self):
        action = load('action')
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(self.client, 'systemctl') as command, \
             patch.object(self.client, 'request') as request:
            for arguments in (['stop'], ['delete-confirmed', 'qwen3:4b']):
                with self.assertRaises(ValueError):
                    action.run(arguments)
            command.assert_not_called()
            request.assert_not_called()

    def test_core_launchers_and_unit_are_reused(self):
        action = load('action')
        with patch.object(action.subprocess, 'Popen') as launch:
            action.run(['setup'])
            self.assertEqual(launch.call_args.args[0], ['/usr/share/eitr/walker/bin/walker', '--provider', 'menus:ai-default'])
            action.run(['chat'])
            self.assertEqual(launch.call_args.args[0], ['python3', '/usr/share/eitr/walker/scripts/actions/ai-assistant.py', 'open'])
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'systemctl', return_value=Mock(returncode=0)) as command:
            action.run(['start'])
            command.assert_called_once_with('start', '--no-block', 'eitr-ollama.service')

    def test_transport_is_fixed_loopback_and_does_not_follow_redirects(self):
        reply = Mock(status=200)
        reply.read.return_value = b'{"models": []}'
        connection = Mock()
        connection.getresponse.return_value = reply
        with patch.object(self.client.http.client, 'HTTPConnection', return_value=connection) as factory, \
             patch.object(self.client.threading, 'Timer') as timer:
            self.assertEqual(self.client.request('ps'), {'models': []})
            factory.assert_called_once_with('127.0.0.1', 11434, timeout=2.5)
            timer.assert_called_once()
            self.assertEqual(timer.call_args.args[0], 2.5)
            timer.return_value.start.assert_called_once()
            connection.request.assert_called_once_with('GET', '/api/ps', body=None, headers={'Content-Type': 'application/json'})
            reply.status = 302
            with self.assertRaises(ValueError):
                self.client.request('tags')
            self.assertEqual(factory.call_count, 2)
            connection.close.assert_called()

    def test_transport_errors_and_size_limit(self):
        connection = Mock()
        reply = Mock(status=200)
        connection.getresponse.return_value = reply
        with patch.object(self.client.http.client, 'HTTPConnection', return_value=connection):
            reply.read.return_value = b'x' * (1024 * 1024 + 1)
            with self.assertRaises(ValueError):
                self.client.request('tags')
            connection.request.side_effect = TimeoutError()
            with self.assertRaises(ValueError):
                self.client.request('tags')

    def test_model_names_are_data_and_remote_registry_names_are_refused(self):
        for value in ('', '--help', 'bad\nmodel', 'http://example/model', '../model',
                      'model;touch /tmp/file', 'model@host', 'model-cloud', 'model:cloud', 'remote.example/model'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.client.model_name(value)
        self.assertEqual(self.client.model_name('library/llama3.2:3b'), 'library/llama3.2:3b')

    def stream(self, lines):
        @contextmanager
        def response(*arguments, **kwargs):
            with io.BytesIO(lines) as reply:
                yield reply
        return response

    def test_stream_progress_persists_after_success(self):
        pull = load('pull')
        lines = b'{"status":"pulling layer","total":100,"completed":50}\n{"status":"success"}\n'
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(self.client, 'response', self.stream(lines)):
            self.assertEqual(pull.download('qwen3:4b'), 0)
        self.assertEqual(self.client.read_state()['state'], 'complete')
        self.assertEqual((self.client.folder() / 'pull.json').stat().st_mode & 0o777, 0o600)

    def test_stream_cancel_closes_connection_and_saves_terminal_state(self):
        pull = load('pull')
        reply = Mock()
        reply.readline.side_effect = pull.Cancelled()
        @contextmanager
        def response(*arguments, **kwargs):
            try:
                yield reply
            finally:
                reply.close()
        with patch.object(self.client, 'configured', return_value=True), \
             patch.object(self.client, 'active', return_value=True), \
             patch.object(self.client, 'response', response):
            self.assertEqual(pull.download('qwen3:4b'), 0)
        self.assertEqual(self.client.read_state()['state'], 'cancelled')
        reply.close.assert_called_once()

    def test_worker_rejects_malformed_error_oversize_and_premature_eof(self):
        pull = load('pull')
        for lines in (b'', b'not json\n', b'{"error":"not found"}\n', b'x' * 17000,
                      b'[]\n', b'{"status":"pulling","total":100}\n'):
            with self.subTest(lines=lines[:30]), \
                 patch.object(self.client, 'configured', return_value=True), \
                 patch.object(self.client, 'active', return_value=True), \
                 patch.object(self.client, 'response', self.stream(lines)):
                self.assertEqual(pull.download('qwen3:4b'), 1)
                self.assertEqual(self.client.read_state()['state'], 'failed')

    def test_worker_lock_refuses_duplicate_without_overwriting_state(self):
        pull = load('pull')
        self.client.write_state({'state': 'downloading', 'model': 'first'})
        with patch.object(pull.fcntl, 'flock', side_effect=BlockingIOError()):
            self.assertEqual(pull.download('second'), 1)
        self.assertEqual(self.client.read_state()['model'], 'first')

    def test_stale_download_is_reported_as_interrupted(self):
        status = load('status')
        self.client.write_state({'state': 'downloading', 'model': 'first'})
        with patch.object(self.client, 'configured', return_value=False), \
             patch.object(self.client, 'active', return_value=False):
            self.assertEqual(status.read()['pull']['state'], 'interrupted')

    def test_inventory_overflow_returns_an_explicit_bounded_error(self):
        status = load('status')
        with self.assertRaises(ValueError):
            status.models({'models': [{'name': 'model'}] * 101})
        encoded = status.encode({'loaded': [{'name': '模型' * 160}] * 100,
                                 'installed': [{'name': '模型' * 160}] * 100, 'pull': {}})
        self.assertLess(len(encoded.encode()), 64 * 1024)
        self.assertTrue(json.loads(encoded)['error'])

    def test_every_translation_has_seven_nonempty_values(self):
        source = (PLUGIN / 'Strings.js').read_text()
        translations = json.loads(source.split('var translations = ', 1)[1].split(';\nfunction', 1)[0])
        self.assertGreater(len(translations), 30)
        for text, values in translations.items():
            self.assertEqual(len(values), 7, text)
            self.assertTrue(all(isinstance(value, str) and value.strip() for value in values), text)

    def test_manifest_refresh_and_core_default(self):
        sys.path.insert(0, str(ROOT.parent / 'eitr/distro/lib'))
        import eitr_plugin_manifest
        manifest = eitr_plugin_manifest.manifest(PLUGIN)
        self.assertNotIn('packages', manifest)
        self.assertNotIn('service', manifest)
        self.assertEqual(manifest['ui']['barItems'][0]['refreshInterval'], 30000)
        self.assertEqual(manifest['ui']['panels'][0]['refreshInterval'], 2000)
        core = (ROOT.parent / 'eitr/distro/lib/eitr_local_assistant.py').read_text()
        self.assertIn("MODEL = '" + self.client.DEFAULT_MODEL + "'", core)
        for source in PLUGIN.iterdir():
            if source.suffix in ('.py', '.qml', '.js'):
                self.assertLessEqual(len(source.read_text().splitlines()), 400, source.name)


if __name__ == '__main__':
    unittest.main()
