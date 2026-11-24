#!/usr/bin/env python3
"""Local panel actions. Only the managed service calls GitHub."""
import html
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

from client import read_json
from storage import RUNTIME, STATE

ROOT = Path(__file__).resolve().parent


def translated(message):
    catalog = (ROOT / "Strings.js").read_text().split("var translations = ", 1)[1].split(";\n", 1)[0]
    language = next((os.environ[key] for key in ("LC_ALL", "LC_MESSAGES", "LANG")
                     if os.environ.get(key)), "").split("_")[0].split(".")[0]
    languages = ("de", "es", "fr", "ja", "ko", "pt", "zh")
    values = json.loads(catalog).get(message)
    return values[languages.index(language)] if values and language in languages else message


# The card header shows the GitHub mark in place of the generic bell (an app icon, not a picture).
ICON = Path(__file__).resolve().with_name("icon.svg").as_uri()


def notify(url, label, login, reason):
    body = html.escape(f"{login} · {translated(reason)}\n{url}")
    response = subprocess.run(
        ["notify-send", "--app-name=GitHub", "--app-icon=" + ICON, "--action=default=" + translated("Open in browser"),
         "--expire-time=10000", "--", label, body],
        capture_output=True, text=True,
    )
    if response.stdout.strip() == "default":
        subprocess.run(["xdg-open", url], check=False, timeout=15)


def send(message):
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
        connection.settimeout(1)
        connection.sendto(json.dumps(message).encode(), str(RUNTIME))


def open_pull(identifier, pr_id):
    snapshot = read_json(STATE / "snapshot.json", {})
    account = next((row for row in snapshot.get("accounts", []) if row["id"] == identifier), None)
    if not account or account["status"] == "signed-out":
        return
    pr = next((row for row in account["rows"] if row["id"] == pr_id), None)
    if pr:
        subprocess.Popen(["xdg-open", pr["url"]])


def main(arguments):
    operation, *values = arguments
    if operation == "notify":
        notify(*values)
    elif operation == "panel":
        subprocess.run(["eitr-shell", "desktop-bar", "ipc", "call", "--", "panels", "plugin", "github"],
                       check=True, timeout=5)
    elif operation == "message":
        send(json.loads(values[0]))
    elif operation == "open":
        open_pull(*values)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError, subprocess.SubprocessError):
        if len(sys.argv) > 1 and sys.argv[1] != "notify":
            try:
                subprocess.run(["notify-send", "--app-name=GitHub", "--app-icon=" + ICON, "GitHub", translated("Action failed")],
                               check=False, timeout=5)
            except (OSError, subprocess.SubprocessError):
                pass
        sys.exit(1)
