"""Machine-local storage and validated plugin preferences."""
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from classify import DEFAULTS
from client import config_root, read_json

CONFIG = config_root() / "plugins" / "github.json"
STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "eitr/plugins/github"
RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR") or STATE) / "eitr-github-radar.sock"
DEFAULT_SETTINGS = {**DEFAULTS, "owners": {}, "collapsed_sections": ["fyi", "waiting"], "notifications": True}


def atomic(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def valid_url(url, host):
    if not isinstance(url, str):
        return False
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    return (parts.scheme == "https" and parts.netloc.casefold() == host.casefold()
            and not parts.query and not parts.fragment and len(segments) == 4
            and all(segments) and segments[2] == "pull" and segments[3].isdigit()
            and not any(character.isspace() or ord(character) < 32 for character in url))


def clean_setting(key, value):
    default = DEFAULT_SETTINGS[key]
    if key == "collapsed_sections":
        allowed = {"own", "others", "fyi", "waiting"}
        if isinstance(value, list):
            sections = [entry for entry in value if entry != "snoozed"]
            if all(isinstance(entry, str) and entry in allowed for entry in sections):
                return list(dict.fromkeys(sections))
    elif key == "team_requests":
        if value in ("until-reviewed", "always", "never"):
            return value
    elif isinstance(default, list):
        if isinstance(value, str):
            value = value.split(",")
        if isinstance(value, list) and all(isinstance(entry, str) for entry in value):
            return [entry.strip() for entry in value[:100] if entry.strip()][:100]
    elif isinstance(default, bool):
        if isinstance(value, bool):
            return value
    raise ValueError(key)


def settings():
    data = read_json(CONFIG, {})
    if not isinstance(data, dict):
        data = {}
    result = dict(DEFAULT_SETTINGS)
    for key in data.keys() & DEFAULT_SETTINGS.keys() - {"owners"}:
        try:
            result[key] = clean_setting(key, data[key])
        except ValueError:
            continue
    if isinstance(data.get("owners"), dict):
        result["owners"] = {account: clean_setting("bots", owners)
                            for account, owners in data["owners"].items()
                            if isinstance(owners, (str, list)) and (
                                isinstance(owners, str) or all(isinstance(owner, str) for owner in owners))}
    return result
