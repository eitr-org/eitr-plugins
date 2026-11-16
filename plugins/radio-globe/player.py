"""Control only the mpv instance on Radio Globe's private Unix socket."""
import json
import shutil
import socket
import subprocess
import time

from browser import AGENT, station
from storage import folder, read, write


def ipc(command):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(0.5)
        connection.connect(str(folder('RUNTIME') / 'mpv.sock'))
        connection.sendall((json.dumps({'command': command, 'request_id': 1}) + '\n').encode())
        payload = b''
        end = time.monotonic() + 0.7
        while time.monotonic() < end and len(payload) < 65536:
            chunk = connection.recv(4096)
            if not chunk:
                break
            payload += chunk
            while b'\n' in payload:
                line, payload = payload.split(b'\n', 1)
                result = json.loads(line)
                if result.get('request_id') == 1:
                    if result.get('error') != 'success':
                        raise RuntimeError('The Radio Globe player could not complete that action')
                    return result.get('data')
        raise RuntimeError('The Radio Globe player did not answer')


def status():
    saved = read(folder('RUNTIME') / 'playing.json', None)
    if not isinstance(saved, dict):
        return None
    try:
        active = ipc(['get_property', 'path'])
        if active != saved.get('url'):
            return None
        return dict(station=saved, volume=round(float(ipc(['get_property', 'volume']))))
    except (OSError, RuntimeError, ValueError):
        return None


def stop():
    try:
        ipc(['quit'])
    except (FileNotFoundError, ConnectionRefusedError):
        pass
    except (RuntimeError, ConnectionResetError):
        # quit can close the socket before mpv acknowledges the command.
        pass
    path = folder('RUNTIME') / 'mpv.sock'
    end = time.monotonic() + 1.5
    while path.exists() and time.monotonic() < end:
        try:
            ipc(['get_property', 'pid'])
        except (FileNotFoundError, ConnectionRefusedError):
            path.unlink(missing_ok=True)
            break
        except (OSError, RuntimeError):
            pass
        time.sleep(0.04)
    if path.exists():
        raise RuntimeError('The previous player is still stopping. Retry in a moment.')
    (folder('RUNTIME') / 'playing.json').unlink(missing_ok=True)


def play(record, volume):
    cleaned = station(record)
    if cleaned is None:
        raise ValueError('Only checked HTTP or HTTPS stations can be played')
    executable = shutil.which('mpv')
    if not executable:
        raise RuntimeError('Install the official mpv package to play stations')
    stop()
    path = folder('RUNTIME') / 'mpv.sock'
    arguments = [executable, '--no-config', '--load-scripts=no', '--ytdl=no', '--no-video',
                 '--audio-display=no', '--no-terminal', '--idle=no', '--network-timeout=8',
                 '--input-default-bindings=no', '--input-vo-keyboard=no',
                 '--user-agent=' + AGENT, '--volume=' + str(volume),
                 '--input-ipc-server=' + str(path), '--', cleaned['url']]
    process = subprocess.Popen(arguments, start_new_session=True, stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        end = time.monotonic() + 1.5
        while not path.exists() and process.poll() is None and time.monotonic() < end:
            time.sleep(0.04)
        if not path.exists() or process.poll() is not None:
            raise RuntimeError('The station player could not start')
        write(folder('RUNTIME') / 'playing.json', cleaned)
    except BaseException:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=0.5)
        raise
    return dict(station=cleaned, volume=volume)


def set_volume(value):
    if status():
        ipc(['set_property', 'volume', value])
