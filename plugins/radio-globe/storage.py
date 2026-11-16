"""Small, private, atomic files owned by Radio Globe."""
import json
import os
from pathlib import Path
import tempfile


def folder(kind):
    defaults = {'CONFIG': Path.home() / '.config', 'CACHE': Path.home() / '.cache'}
    base = os.environ.get('XDG_' + kind + '_HOME') if kind != 'RUNTIME' else os.environ.get('XDG_RUNTIME_DIR')
    if not base and kind == 'RUNTIME':
        raise RuntimeError('XDG_RUNTIME_DIR is required for playback')
    path = (Path(base) if base else defaults[kind]) / 'eitr' / 'plugins' / 'radio-globe'
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    return path


def read(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default
    except (ValueError, UnicodeError) as error:
        raise RuntimeError('Could not read saved Radio Globe data') from error


def write(path, data):
    descriptor, name = tempfile.mkstemp(dir=path.parent, prefix='.radio-')
    try:
        with os.fdopen(descriptor, 'w') as output:
            json.dump(data, output, ensure_ascii=False, separators=(',', ':'))
            output.write('\n')
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
