"""Bounded loopback-only Ollama transport and the existing Eitr service contract."""
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import threading

UNIT = 'eitr-ollama.service'
PULL_UNIT = 'eitr-ollama-plugin-pull.service'
DEFAULT_MODEL = 'qwen3:4b'
CODE = Path('/usr/share/eitr')
MODEL_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9][A-Za-z0-9._-]*)?\Z')


def model_name(value):
    if not isinstance(value, str) or len(value) > 160 or not MODEL_NAME.fullmatch(value) or '..' in value:
        raise ValueError('Use a model name such as llama3.2:3b.')
    if value.endswith(('-cloud', ':cloud')) or '.' in value.split('/')[0] and '/' in value:
        raise ValueError('Use a local library model, without a registry address.')
    return value


def folder():
    return Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'eitr/ollama-plugin'


def read_state():
    try:
        payload = json.loads((folder() / 'pull.json').read_text()[:8192])
        return payload if isinstance(payload, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(payload):
    directory = folder()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = directory / ('pull.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(payload))
    temporary.chmod(0o600)
    temporary.replace(directory / 'pull.json')


def systemctl(*arguments, timeout=1):
    return subprocess.run(['systemctl', '--user', *arguments], capture_output=True,
                          text=True, timeout=timeout, check=False)


def active(unit=UNIT):
    return systemctl('is-active', '--quiet', unit).returncode == 0


def configured():
    configuration = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    return shutil.which('ollama') is not None and (configuration / 'systemd/user' / UNIT).is_file()


def ready():
    result = subprocess.run([sys.executable, str(CODE / 'walker/scripts/actions/ai-assistant.py'),
                             'local-state'], capture_output=True, text=True, timeout=1.5, check=False)
    return result.returncode == 0 and result.stdout.strip() == 'ready'


@contextmanager
def response(endpoint, body=None, *, method=None, deadline=2.5, idle=2.5):
    if endpoint not in ('ps', 'tags', 'pull', 'delete', 'generate'):
        raise ValueError('Unsupported API endpoint.')
    connection = http.client.HTTPConnection('127.0.0.1', 11434, timeout=idle)
    def expire():
        if connection.sock:
            try:
                connection.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        connection.close()
    timer = threading.Timer(deadline, expire)
    timer.daemon = True
    timer.start()
    try:
        encoded = json.dumps(body).encode() if body is not None else None
        connection.request(method or ('POST' if encoded else 'GET'), '/api/' + endpoint,
                           body=encoded, headers={'Content-Type': 'application/json'})
        reply = connection.getresponse()
        if reply.status != 200:
            raise ValueError('Ollama rejected the request (HTTP ' + str(reply.status) + ').')
        yield reply
    except (OSError, http.client.HTTPException) as error:
        raise ValueError('Ollama is unavailable or the request timed out.') from error
    finally:
        timer.cancel()
        connection.close()


def request(endpoint, body=None, *, method=None):
    with response(endpoint, body, method=method) as reply:
        raw = reply.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('Ollama returned too much data.')
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict) or payload.get('error'):
            raise ValueError('Ollama could not complete the request.')
        return payload
