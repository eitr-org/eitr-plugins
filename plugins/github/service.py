#!/usr/bin/env python3
"""Eitr-managed background poller. Visuals only read the local projection."""
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import socket
import subprocess
import time
import json

from classify import classify, notification
from client import GitHub, RateLimited, SignedOut, Unavailable, accounts, read_json
from storage import (CONFIG, DEFAULT_SETTINGS, RUNTIME, STATE, atomic,
                     clean_setting, settings, valid_url)

POLL = 300
FULL = 3600
ACTION = Path(__file__).with_name("action.py")


def refresh(account, cache, options, now, force=False, client_factory=GitHub):
    if cache.get("host") != account["host"]:
        cache = {"host": account["host"]}
    if cache.get("reset", 0) > now:
        return cache
    cache = {**cache, "reset": 0}
    client = client_factory(account)
    try:
        if not cache.get("login") or now >= cache.get("identity_at", 0) + FULL or force:
            login = client.identity()
            if login != cache.get("login"):
                cache = {"host": account["host"], "login": login, "reset": 0}
            cache["identity_at"] = now
        login = cache["login"]
        if "teams" not in cache or now >= cache.get("teams_at", 0) + FULL:
            try:
                cache["teams"] = client.teams()
            except RateLimited:
                raise
            except Unavailable:
                cache.setdefault("teams", [])
            cache["teams_at"] = now
        owners = {owner.casefold() for owner in options["owners"].get(account["id"], [])}
        found = {pr["id"]: pr for pr in client.search(login)
                 if not owners or pr["repository"]["nameWithOwner"].split("/")[0].casefold() in owners}
        old = cache.get("pulls", {})
        full = force or "full_at" not in cache or now >= cache["full_at"] + FULL
        changed = [identifier for identifier, item in found.items()
                   if full or identifier not in old or item["updatedAt"] != old[identifier].get("searched")]
        pulls = {identifier: old[identifier] for identifier in found if identifier not in changed}
        for pr in client.details(changed, login):
            if valid_url(pr["url"], account["host"]):
                pulls[pr["id"]] = dict(pr, searched=found[pr["id"]]["updatedAt"])
        cache.update(pulls=pulls, status="ok", reset=0, updated_at=now)
        if full:
            cache["full_at"] = now
    except SignedOut:
        return {"host": account["host"], "status": "signed-out"}
    except RateLimited as error:
        cache.update(status="rate-limited", reset=error.reset)
    except Unavailable:
        cache["status"] = "unavailable"
    return cache


def project(account, cache, options, state, now):
    result = {key: account[key] for key in ("label", "id")}
    result.update(login=cache.get("login", ""), status=cache.get("status", "loading"),
                  reset=cache.get("reset", 0), updated_at=cache.get("updated_at", 0), rows=[], count=0)
    identity = [account["host"], result["login"]]
    if state.get("identity") != identity and result["login"]:
        state.clear()
        state["identity"] = identity
    history = state.setdefault("history", {})
    alerts = []
    waiting = state.setdefault("waiting", {})
    for identifier, pr in sorted(cache.get("pulls", {}).items(),
                                 key=lambda pair: pair[1]["updated"], reverse=True):
        assessment = classify(pr, result["login"], cache.get("teams", []), options)
        if result["status"] == "ok":
            seen = history.get(identifier)
            history[identifier], alert = notification(seen, assessment, state.get("seeded", False))
            group = assessment["group"]
            previous = waiting.get(identifier)
            request_at = assessment["details"].get("requested_at")
            if group >= 2:
                waiting.pop(identifier, None)
            elif (not previous or previous["group"] != group
                  or (request_at and request_at != previous.get("request_at"))):
                observed = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                initial = not state.get("seeded") or (seen and seen[0] == group and not previous)
                since = request_at or (pr["updated"] if initial else observed)
                waiting[identifier] = {"group": group, "since": since, "request_at": request_at}
            if alert and options.get("notifications", True):
                alerts.append((pr["url"], result["label"], result["login"], assessment["reasons"][0]))
        row = {key: value for key, value in pr.items() if key not in {"threads", "searched", "review_requested"}}
        row.update(assessment)
        row["waiting_since"] = waiting.get(identifier, {}).get("since", pr["updated"])
        result["rows"].append(row)
        result["count"] += assessment["group"] < 2
    if result["status"] == "ok":
        state["seeded"] = True
        for records in (history, waiting):
            for identifier in records.keys() - cache["pulls"].keys():
                del records[identifier]
    return result, alerts


class Radar:
    def __init__(self):
        self.cache = read_json(STATE / "cache.json", {})
        self.state = read_json(STATE / "state.json", {})
        for record in self.state.values():
            record.pop("snoozes", None)
        self.options = settings()
        self.selection_path = STATE / "selected-account.json"
        self.selected_account = read_json(self.selection_path, "")
        self.repositories_path = STATE / "selected-repositories.json"
        saved_repositories = read_json(self.repositories_path, {})
        self.selected_repositories = saved_repositories if isinstance(saved_repositories, dict) else {}
        self.snapshot = read_json(STATE / "snapshot.json", {})
        self.force = False
        self.poll_at = 0

    def update(self, poll=False):
        self.options = settings()
        now = time.time()
        active = accounts()
        if poll:
            atomic(STATE / "snapshot.json", {**self.snapshot, "refreshing": True})
        updated_at = self.snapshot.get("updated_at")
        if poll:
            previous = self.cache
            self.cache = {}
            for account in active:
                identifier = account["id"]
                cached = previous.get(identifier, {})
                if self.force or now >= cached.get("next_at", 0) or cached.get("host") != account["host"]:
                    cached = refresh(account, cached, self.options, now, self.force)
                    cached["next_at"] = cached.get("reset") or time.time() + POLL
                self.cache[identifier] = cached
            updated_at = max((cached.get("updated_at", 0) for cached in self.cache.values()), default=0)
            self.force = False
            self.poll_at = now + POLL
            atomic(STATE / "cache.json", self.cache)
        projected = []
        alerts = []
        for account in active:
            identifier = account["id"]
            summary, new_alerts = project(account, self.cache.get(identifier, {}), self.options,
                                          self.state.setdefault(identifier, {}), now)
            projected.append(summary)
            alerts.extend(new_alerts)
        selections = dict(self.selected_repositories)
        for summary in projected:
            identifier = summary["id"]
            if (identifier in selections and summary["status"] == "ok"
                    and not any(row["repo"] == selections[identifier] for row in summary["rows"])):
                del selections[identifier]
        self.save_repositories(selections)
        self.snapshot = {"accounts": projected, "count": sum(row["count"] for row in projected),
                         "options": self.options, "updated_at": updated_at, "refreshing": False,
                         "selected_account": self.selected_account,
                         "selected_repositories": self.selected_repositories}
        atomic(STATE / "state.json", self.state)
        atomic(STATE / "snapshot.json", self.snapshot)
        for url, label, login, reason in alerts:
            subprocess.Popen([str(ACTION), "notify", url, label, login, reason],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def save_repositories(self, selections):
        if selections != self.selected_repositories:
            atomic(self.repositories_path, selections)
            self.selected_repositories = selections

    def handle(self, message):
        operation = message.get("operation")
        if operation == "refresh":
            self.force = True
            self.poll_at = 0
            return
        identifier = message.get("account")
        account = next((row for row in self.snapshot["accounts"] if row["id"] == identifier), None)
        if operation == "select-account" and account:
            atomic(self.selection_path, identifier)
            self.selected_account = identifier
            self.snapshot = {**self.snapshot, "selected_account": identifier}
            atomic(STATE / "snapshot.json", self.snapshot)
        if operation == "select-repository" and account:
            repository = message.get("repository")
            selections = dict(self.selected_repositories)
            if repository == "":
                selections.pop(identifier, None)
            elif any(row["repo"] == repository for row in account["rows"]):
                selections[identifier] = repository
            else:
                return
            self.save_repositories(selections)
            self.snapshot = {**self.snapshot, "selected_repositories": self.selected_repositories}
            atomic(STATE / "snapshot.json", self.snapshot)
        if operation == "setting":
            key, value = message.get("key"), message.get("value")
            options = settings()
            if key == "owners" and account:
                options["owners"][identifier] = clean_setting("bots", value)
                self.cache.get(identifier, {}).pop("next_at", None)
                self.poll_at = 0
            elif key in DEFAULT_SETTINGS and key != "owners":
                options[key] = clean_setting(key, value)
            else:
                return
            atomic(CONFIG, options)
            self.update()

    def run(self, connection):
        while True:
            now = time.time()
            due = self.next_poll()
            if due <= now:
                self.update(poll=True)
                # A successful poll itself may have taken longer than a short backoff.
                now = time.time()
            connection.settimeout(max(0.1, self.next_poll() - now))
            try:
                message = json.loads(connection.recv(16384))
                if isinstance(message, dict):
                    self.handle(message)
            except (socket.timeout, ValueError, TypeError):
                continue

    def next_poll(self):
        return min([self.poll_at, *(cached.get("next_at", 0) for cached in self.cache.values())])


def main():
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "service.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        RUNTIME.unlink(missing_ok=True)
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as connection:
            connection.bind(str(RUNTIME))
            try:
                Radar().run(connection)
            finally:
                RUNTIME.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
