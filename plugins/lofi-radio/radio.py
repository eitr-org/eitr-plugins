#!/usr/bin/env python3
"""Launch one terminal player; control only the process started by this plugin."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


INSTALL = 'Install lowfi in Walker > Install > Packages > Yay (AUR); search lowfi.'


def notify(message):
    subprocess.run(['notify-send', 'Lofi Radio', message], check=False)


SCRATCHPAD = 'lofi'
WINDOW = "hl.get_window('class:^(eitr-lofi-radio)$')"


def hypr(expression):
    return subprocess.run(['hyprctl', 'eval', expression], capture_output=True, text=True, check=False)


def hide_when_open():
    """The bar's media controls drive playback, so the player waits in a scratchpad."""
    for attempt in range(50):
        if hypr(f'local window = {WINDOW}; assert(window)').returncode == 0:
            hypr(f'local window = {WINDOW}; hl.dispatch(hl.dsp.window.move({{window=window, '
                 f"workspace='special:{SCRATCHPAD}', follow=false}}))")
            return
        time.sleep(0.1)


def identity(process_id):
    try:
        return Path(f'/proc/{process_id}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def main():
    action = sys.argv[1]
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if not runtime:
        raise RuntimeError('XDG_RUNTIME_DIR is required')
    folder = Path(runtime) / 'eitr-lofi-radio'
    folder.mkdir(mode=0o700, exist_ok=True)
    state = folder / 'player.json'
    with (folder / 'lock').open('w') as lock:
        if action == 'play':
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            player = subprocess.Popen(['lowfi'])
            state.write_text(json.dumps([player.pid, identity(player.pid)]))

            def stop(signum, frame):
                player.terminate()

            signal.signal(signal.SIGTERM, stop)
            try:
                player.wait()
            finally:
                state.unlink(missing_ok=True)
            return
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if action == 'open':
                hypr(f"hl.dispatch(hl.dsp.workspace.toggle_special('{SCRATCHPAD}'))")
                return
            try:
                process_id, started = json.loads(state.read_text())
                descriptor = os.pidfd_open(process_id)
                try:
                    if started is not None and identity(process_id) == started:
                        signal.pidfd_send_signal(descriptor, signal.SIGTERM)
                finally:
                    os.close(descriptor)
            except (FileNotFoundError, ProcessLookupError):
                notify('Player is starting or stopping; try again in a moment.')
            return
        if not shutil.which('lowfi'):
            notify(INSTALL)
            return
        subprocess.Popen(['kitty', '--class', 'eitr-lofi-radio', '--title', 'Lofi Radio',
                          '-e', sys.executable, str(Path(__file__).resolve()), 'play'],
                         start_new_session=True, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if action == 'toggle':
            hide_when_open()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        notify(str(error))
        sys.exit(1)
