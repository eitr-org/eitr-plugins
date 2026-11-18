"""Offline clock arithmetic, preferences and manifest contract."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'eitr/distro/lib'))
spec = importlib.util.spec_from_file_location('world_clock', ROOT / 'plugins/world-clock/runtime.py')
clock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clock)


class WorldClockTests(unittest.TestCase):
    def settings(self, zone='Europe/Lisbon'):
        return {'barCount': 2, 'cities': [{'zone': zone, 'label': 'LIS'}]}

    def test_dst_transition_changes_time_and_offset(self):
        before = datetime(2026, 3, 29, 0, 59, tzinfo=timezone.utc)
        after = datetime(2026, 3, 29, 1, 0, tzinfo=timezone.utc)
        first, = clock.clock_rows(self.settings(), before, timezone.utc)
        second, = clock.clock_rows(self.settings(), after, timezone.utc)
        self.assertEqual((first['time24'], first['offset']), ('00:59', '+0 h'))
        self.assertEqual((second['time24'], second['offset']), ('02:00', '+1 h'))
        # Fall-back repeats an hour, while the offset distinguishes both instants.
        first, = clock.clock_rows(self.settings(), datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc), timezone.utc)
        second, = clock.clock_rows(self.settings(), datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc), timezone.utc)
        self.assertEqual(first['time24'], second['time24'])
        self.assertEqual((first['offset'], second['offset']), ('+1 h', '+0 h'))

    def test_local_dst_and_fractional_offsets(self):
        instant = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)
        row, = clock.clock_rows(self.settings('Asia/Kolkata'), instant, ZoneInfo('America/New_York'))
        self.assertEqual((row['time24'], row['time12'], row['offset']), ('17:30', '5:30 PM', '+9 h 30'))
        row, = clock.clock_rows(self.settings('America/New_York'), instant, ZoneInfo('Asia/Kolkata'))
        self.assertEqual(row['offset'], '-9 h 30')

    def test_date_line_yesterday_and_tomorrow(self):
        instant = datetime(2026, 1, 1, 11, tzinfo=timezone.utc)
        row, = clock.clock_rows(self.settings('Pacific/Kiritimati'), instant, ZoneInfo('Pacific/Honolulu'))
        self.assertEqual(row['day'], 'Tomorrow')
        row, = clock.clock_rows(self.settings('Pacific/Honolulu'), instant, ZoneInfo('Pacific/Kiritimati'))
        self.assertEqual(row['day'], 'Yesterday')
        row, = clock.clock_rows(self.settings(), instant, timezone.utc)
        self.assertEqual(row['day'], 'Today')

    def test_bar_counts_states_and_duplicate_zones(self):
        for count in range(1, 11):
            self.assertEqual(clock.validate({'barCount': count, 'cities': []})['barCount'], count)
        results = clock.search('california')
        state = results[0]
        city = next(result for result in results if result['name'] == 'Los Angeles')
        self.assertEqual((state['kind'], state['zoneCity'], state['label']), ('state', 'Los Angeles', 'CAL'))
        self.assertEqual(city['name'], 'Los Angeles')
        settings = {'barCount': 10, 'cities': [{key: result[key] for key in ('zone', 'label', 'name', 'country')} for result in (state, city)]}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}):
            clock.save_settings(settings)
            self.assertEqual(clock.read_settings(), settings)
        self.assertNotEqual(*[row['key'] for row in clock.clock_rows(settings)])
        with self.assertRaises(ValueError):
            clock.validate({**settings, 'cities': [settings['cities'][0]] * 2})

    def test_stream_reemits_after_save_and_removal(self):
        import selectors
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ, XDG_CONFIG_HOME=directory)
            process = subprocess.Popen([sys.executable, str(ROOT / 'plugins/world-clock/runtime.py'), 'stream'], env=environment, stdout=subprocess.PIPE)
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            def receive():
                self.assertTrue(selector.select(3), 'No stream update within three seconds')
                return json.loads(process.stdout.readline())
            try:
                self.assertEqual(receive()['cities'], [])
                with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}):
                    clock.save_settings(self.settings())
                    self.assertEqual(len(receive()['cities']), 1)
                    clock.save_settings({'barCount': 10, 'cities': []})
                    self.assertEqual(receive()['cities'], [])
                    clock.settings_path().unlink()
                    self.assertEqual(receive()['barCount'], 1)
            finally:
                process.terminate()
                process.wait(timeout=3)
                process.stdout.close()
                selector.close()

    def test_minute_alignment(self):
        self.assertEqual(clock.minute_delay(120), 60)
        self.assertAlmostEqual(clock.minute_delay(123.75), 56.25)
        self.assertGreater(clock.minute_delay(179.999), 0)

    def test_atomic_settings_round_trip_preserves_order_and_labels(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}):
            self.assertEqual(clock.read_settings(), {'cities': [], 'barCount': 1})
            settings = self.settings()
            settings['cities'].insert(0, {'zone': 'Asia/Tokyo', 'label': '東京'})
            clock.save_settings(settings)
            self.assertEqual(clock.read_settings(), settings)
            self.assertEqual(list(clock.settings_path().parent.glob('.world-clock-*')), [])
            clock.settings_path().write_text('broken')
            with self.assertRaises(ValueError):
                clock.read_settings()
            self.assertIn('error', clock.snapshot())
            self.assertEqual(clock.settings_path().read_text(), 'broken')

    def test_reject_invalid_settings_without_writes(self):
        for settings in [
                {'cities': [], 'barCount': True},
                {'cities': [], 'barCount': 11},
                {'cities': [{'zone': '../../etc/passwd', 'label': 'bad'}], 'barCount': 1},
                {'cities': [{'zone': 'UTC', 'label': '\n'}], 'barCount': 1},
                {'cities': [{'zone': 'UTC', 'label': 'A'}] * 2, 'barCount': 1},
                {'cities': [{'zone': 'UTC', 'label': 'a' * 13}], 'barCount': 1}]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                clock.validate(settings)

    def test_stream_fits_and_passes_the_desktop_line_transport(self):
        from eitr_plugin_stream import Lines, MAX_LINE
        longest_zones = sorted(clock.available_timezones(), key=len, reverse=True)[:clock.MAX_CITIES]
        settings = {'barCount': 2, 'cities': [{'zone': zone, 'label': '🌍' * 12} for zone in longest_zones]}
        with patch.object(clock, 'read_settings', return_value=settings):
            line = clock.stream_snapshot()
        encoded = line.encode('utf-8')
        self.assertLessEqual(len(encoded), MAX_LINE)
        accepted = Lines().feed(encoded + b'\n', 1)
        self.assertEqual(accepted, [line])
        self.assertNotIn('zones', json.loads(line))
        self.assertEqual(len(json.loads(line)['cities']), clock.MAX_CITIES)

    def test_manifest_clock_slot_and_stream(self):
        import eitr_plugin_manifest
        manifest = eitr_plugin_manifest.manifest(ROOT / 'plugins/world-clock')
        item, = manifest['ui']['barItems']
        self.assertEqual(item['slot'], 'clock')
        self.assertEqual(item['dataStream']['arguments'], ['stream'])
        self.assertNotIn('refreshInterval', item)
        self.assertNotIn('packages', manifest)
        self.assertNotIn('service', manifest)
        self.assertLess(len(json.dumps({'zones': sorted(clock.available_timezones())})), 65536)

    def test_search_examples_ranking_and_accents(self):
        self.assertEqual(clock.search('sao paulo'), clock.search('São Paulo'))
        self.assertEqual(clock.search('SÃO PAULO')[0]['name'], 'São Paulo')
        self.assertEqual((clock.search('porto')[0]['name'], clock.search('porto')[0]['country']), ('Porto', 'PT'))
        california = clock.search('california')
        self.assertEqual(california[0]['name'], 'California')
        self.assertEqual(california[0]['zone'], 'America/Los_Angeles')
        self.assertTrue(any(city['name'] == 'Los Angeles' for city in california))
        brazil = clock.search('brazil')
        self.assertEqual(brazil[0]['name'], 'São Paulo')
        self.assertGreater(len({city['zone'] for city in brazil}), 1)
        self.assertEqual(clock.search('tokyo')[0]['zone'], 'Asia/Tokyo')
        self.assertEqual(clock.search('Europe/Lisbon')[0]['zone'], 'Europe/Lisbon')
        self.assertEqual(clock.search('UTC')[0]['zone'], 'UTC')
        self.assertEqual(clock.search(''), [])
        self.assertEqual(clock.search('no such city xyz'), [])
        self.assertLessEqual(len(clock.search('a')), 30)
        with self.assertRaises(ValueError):
            clock.search('a' * 101)
        with self.assertRaises(ValueError):
            clock.search('\n')
        for query in ('porto', 'brazil', 'california'):
            self.assertLess(len(json.dumps(clock.search(query)).encode()), 65536)

    def test_city_metadata_flags_and_validation(self):
        city = clock.search('Europe/Lisbon')[0]
        settings = {'barCount': 1, 'cities': [{key: city[key] for key in ('zone', 'label', 'name', 'country')}]}
        self.assertEqual(clock.validate(settings), settings)
        self.assertEqual(clock.clock_rows(settings)[0]['flag'], '🇵🇹')
        self.assertEqual(clock.flag('JP'), '🇯🇵')
        self.assertEqual(clock.flag(''), '')
        self.assertEqual(clock.flag('1A'), '')
        for changes in ({'country': 'ZZ'}, {'country': []}, {'name': 'x' * 201}, {'name': '\n'}, {'extra': True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                clock.validate({'barCount': 1, 'cities': [{**settings['cities'][0], **changes}]})
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}):
            clock.save_settings(settings)
            self.assertEqual(clock.read_settings(), settings)
        longest = sorted(clock.zones(), key=len, reverse=True)[:24]
        with patch.object(clock, 'read_settings', return_value={'barCount': 2, 'cities': [
                {'zone': zone, 'label': '🌍' * 12, 'name': 'x' * 200, 'country': 'JP'} for zone in longest]}):
            self.assertLessEqual(len(clock.stream_snapshot().encode()), 4096)

    def test_generator_reproducible_and_filters_unknown_zones(self):
        import gzip
        generator_spec = importlib.util.spec_from_file_location('clock_generator', ROOT / 'tools/build_world_clock_data.py')
        generator = importlib.util.module_from_spec(generator_spec)
        generator_spec.loader.exec_module(generator)
        source = ROOT.parent / 'data'
        if not source.is_dir():
            self.skipTest('Local GeoNames source files required for regeneration')
        generated = generator.build(source)
        self.assertEqual(generated, clock.catalog())
        self.assertEqual(generator.build(source, set())['cities'], [])
        self.assertTrue(all(city[4] in clock.zones() for city in generated['cities']))
        encoded = json.dumps(generated, ensure_ascii=False, separators=(',', ':')).encode()
        self.assertEqual(gzip.compress(encoded, mtime=0), (ROOT / 'plugins/world-clock/data/cities.json.gz').read_bytes())
        self.assertIs(clock.catalog(), clock.catalog())
        self.assertIs(clock.search_index(), clock.search_index())
