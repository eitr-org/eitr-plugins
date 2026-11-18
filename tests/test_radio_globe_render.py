"""Compile and render the plugin with Eitr's real shared controls, offscreen."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest


@unittest.skipUnless(shutil.which('quickshell'), 'Quickshell is required for offscreen QML')
class RadioRenderTests(unittest.TestCase):
    def test_dark_light_panel_and_bar(self):
        source = Path(__file__).resolve().parents[1] / 'tools/radio-globe/render.py'
        spec = importlib.util.spec_from_file_location('radio_globe_render', source)
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        with tempfile.TemporaryDirectory() as temporary:
            for light in (False, True):
                output = Path(temporary) / ('light.png' if light else 'dark.png')
                with self.subTest(light=light):
                    renderer.render(output, light=light)
                    self.assertTrue(output.is_file())
                    self.assertTrue(output.with_name(output.stem + '-bar.png').is_file())
            renderer.render(Path(temporary) / 'closed.png', scenario='lifecycle')
            renderer.render(Path(temporary) / 'portuguese.png', locale='pt_BR')
            renderer.render(Path(temporary) / 'offline.png', scenario='offline')
