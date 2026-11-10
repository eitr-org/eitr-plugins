"""Small adapter to the installed Eitr task terminal and reviewed wizard."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/usr/share/eitr')
sys.path.insert(0, str(ROOT / 'lib'))
from eitr_terminal import wait_for_escape
from eitr_wizard import Cancelled, Step, collect


def run(arguments, *, input=None, timeout=45):
    result = subprocess.run(arguments, input=input, text=True, capture_output=True,
                            timeout=timeout, env={**os.environ, 'LC_ALL': 'C'})
    if result.returncode:
        raise RuntimeError('Operation failed. Check permissions, the selected profile and service availability. Details are hidden to protect credentials.')
    return result.stdout


def choose(title, options):
    if not options:
        raise RuntimeError('No matching profiles or devices were found.')
    return collect(title, [Step('choice', title, options=options)])['choice']


def open_terminal(action):
    """Run this script's ACTION again in Eitr's task terminal, detached."""
    subprocess.Popen([str(ROOT / 'walker/bin/menu-path/kitty'), '--class', 'eitr-menu-terminal',
                      '--title', Path(__file__).parent.name, '-e', sys.executable,
                      str(ROOT / 'walker/scripts/actions/task-terminal.py'), sys.executable,
                      str(Path(sys.argv[0]).resolve()), action, '--terminal'],
                     start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def launch(main):
    if '--terminal' not in sys.argv:
        open_terminal(sys.argv[1])
        return
    try:
        main(sys.argv[1])
    except (Cancelled, KeyboardInterrupt):
        return
    except RuntimeError as error:
        print(str(error))
        print('For permission errors, use Allow this account to control Tailscale.')
        wait_for_escape()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('Operation failed. Check the required tools, permissions and service. Configuration details are hidden to protect credentials.')
        wait_for_escape()
        return
