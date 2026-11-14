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
                {'cities': [], 'barCount': 3},
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
