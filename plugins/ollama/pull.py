#!/usr/bin/env python3
"""One detached streaming download, with an atomic progress record and cancellation."""
import fcntl
import json
import signal
import sys
import time
import client


class Cancelled(BaseException):
    pass


def cancel(signum, frame):
    raise Cancelled()


def download(model):
    model = client.model_name(model)
    client.folder().mkdir(parents=True, exist_ok=True, mode=0o700)
    with (client.folder() / 'pull.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 1
        progress = {'state': 'downloading', 'model': model, 'status': '', 'total': 0, 'completed': 0}
        last_write = 0
        try:
            client.write_state(progress)
            if not client.configured() or not client.active():
                raise ValueError('Start Eitr’s Ollama service before downloading.')
            with client.response('pull', {'model': model, 'stream': True}, deadline=86400, idle=30) as reply:
                while True:
                    line = reply.readline(16385)
                    if not line:
                        raise ValueError('The download stream ended before success.')
                    if len(line) > 16384:
                        raise ValueError('Ollama returned an oversized progress record.')
                    record = json.loads(line)
                    if not isinstance(record, dict) or record.get('error'):
                        raise ValueError('Ollama could not download this model. Check its name and connection.')
                    progress['status'] = str(record.get('status', ''))[:160]
                    for key in ('total', 'completed'):
                        progress[key] = max(0, record.get(key, 0)) if type(record.get(key)) is int else 0
                    if progress['status'] == 'success':
                        progress['state'] = 'complete'
                        break
                    now = time.monotonic()
                    if now - last_write >= 0.25:
                        client.write_state(progress)
                        last_write = now
        except Cancelled:
            progress.update(state='cancelled', status='')
        except (Exception, KeyboardInterrupt):
            progress.update(state='failed', status='Download failed. Check the model name, service and connection, then retry.')
        finally:
            client.write_state(progress)
        return 0 if progress['state'] in ('complete', 'cancelled') else 1


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: pull.py MODEL')
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    raise SystemExit(download(sys.argv[1]))
