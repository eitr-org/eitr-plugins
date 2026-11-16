"""Render plugin QML with real Eitr controls and inert data, outside the live session."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BAR = ROOT.parent / 'eitr/quickshell/desktop-bar'
sys.path.insert(0, str(BAR / 'tests'))
from layout_render import copy_runtime, render_environment


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell required for offscreen renders')
class PhoneRenderTests(unittest.TestCase):
    def test_panel_bar_and_setup_in_both_themes(self):
        output = Path(os.environ.get('PHONE_LINK_RENDERS', '/tmp/phone-link-renders'))
        output.mkdir(parents=True, exist_ok=True)
        plugins = ['kdeconnect_share', 'kdeconnect_findmyphone', 'kdeconnect_ping', 'kdeconnect_sftp']
        devices = [dict(id=identifier, name=name, type=kind, battery=battery, paired=paired,
                        reachable=reachable, charging=charging, incoming=incoming, outgoing=False,
                        verification='123456' if incoming else '', plugins=plugins[:-1] if paired and reachable else [])
                   for identifier, name, kind, battery, paired, reachable, charging, incoming in [
                       ('phone', 'Galaxy S23 Ultra', 'phone', 44, True, True, False, False),
                       ('request', 'New phone', 'phone', None, False, True, False, True),
                       ('tablet', 'Tablet', 'tablet', None, True, False, False, False),
                       ('iphone', 'iPhone', 'phone', None, False, True, False, False)]]
        sample = json.dumps(dict(state='ready', devices=devices, total=len(devices)))
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            copy_runtime(folder)
            shutil.copytree(ROOT / 'plugins/phone-link', folder / 'phone')
            # The fixture displays inert data and never invokes a plugin action.
            edge = [dict(devices[0], id='charging', battery=92, charging=True),
                    dict(devices[0], id='unknown', name='A very long connected tablet name to check elision',
                         type='tablet', battery=None)]
            fixture = (ROOT / 'tests/fixtures/PhoneRender.qml').read_text()
            fixture = fixture.replace('SAMPLE', sample).replace('OUTPUT', str(output))
            fixture = fixture.replace('EDGE', json.dumps(dict(state='ready', devices=edge, total=2)))
            (folder / 'PhoneRender.qml').write_text(fixture)
            environment = render_environment(folder)
            environment['LANG'] = 'en_US.UTF-8'
            try:
                result = subprocess.run(['quickshell', '--no-color', '-p', str(folder / 'PhoneRender.qml')],
                                        env=environment, text=True, capture_output=True, timeout=25)
            except subprocess.TimeoutExpired as error:
                self.fail((error.stdout or b'').decode() + (error.stderr or b'').decode())
            log = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, log)
            self.assertIn('PHONE_RENDER_OK', log)
            for warning in ('ReferenceError', 'TypeError', 'is not a type', 'Failed to load', 'Error:', 'Unable to assign'):
                self.assertNotIn(warning, log)
        from PIL import Image
        for theme in ('dark', 'light'):
            with Image.open(output / ('panel-' + theme + '.png')) as panel:
                self.assertEqual(panel.width, 420)
                self.assertGreater(panel.height, 400)
                self.assertGreater(len(panel.getcolors(panel.width * panel.height)), 10)


if __name__ == '__main__':
    unittest.main()
