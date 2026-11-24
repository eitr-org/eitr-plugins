"""PR radar behavior with isolated state and fake GitHub responses."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/github"
ACCOUNT = {"id": "a" * 32, "host": "github.com", "label": "Studio"}
PEER = {"login": "lark"}
SELF = {"login": "finch"}
TEAM = "paper-finch/editors"


def load(name):
    spec = importlib.util.spec_from_file_location("github_" + name, PLUGIN / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with patch.dict(sys.modules):
    classifier = sys.modules["classify"] = load("classify")
    client = sys.modules["client"] = load("client")
    storage = sys.modules["storage"] = load("storage")
    service = load("service")
    actions = load("action")


def pull(**overrides):
    return {
        "id": "pr-1", "author": "wren", "number": 7, "title": "Restore bookmarks",
        "url": "https://github.com/paper-finch/books/pull/7", "repo": "paper-finch/books",
        "updated": "2026-11-23T15:00:00Z", "ci": "PENDING", "head": "def",
        "reviews": [], "threads": [], **overrides,
    }


def review(actor, state, commit="abc"):
    return {**actor, "state": state, "commit": commit}


def assessment(pr, **options):
    return classifier.classify(pr, "finch", [TEAM], options)


class ClassificationTests(unittest.TestCase):
    def test_default_and_draft(self):
        self.assertEqual(assessment(pull())["group"], 3)
        own = assessment(pull(author="finch"))
        self.assertEqual(own["group"], 3)
        for author in ("finch", "wren"):
            pr = pull(author=author, draft=True, requests=["finch"], conflict=True, ci="FAILURE")
            self.assertEqual(assessment(pr)["group"], 3)

    def test_owned_readiness_failure_and_conflict_defaults(self):
        cases = [
            ("ready", "Ready to merge", {"decision": "APPROVED", "ci": "SUCCESS", "merge": "CLEAN"}),
            ("failure", "CI failed", {"ci": "FAILURE"}),
            ("conflict", "Merge conflict", {"conflict": True}),
        ]
        for setting, reason, fields in cases:
            with self.subTest(setting=setting):
                pr = pull(author="finch", **fields)
                self.assertEqual(assessment(pr)["reasons"], [reason])
                self.assertEqual(assessment(pr)["group"], 0)
                self.assertEqual(assessment(pr, **{setting: False})["group"], 2)
        for merge in ("UNKNOWN", "BLOCKED", "BEHIND", "UNSTABLE"):
            self.assertEqual(assessment(pull(author="finch", decision="APPROVED", ci="SUCCESS",
                                             merge=merge))["group"], 3)

    def test_review_threads_follow_latest_human_reply(self):
        thread = {"resolved": False, "comments": [PEER, SELF]}
        pr = pull(author="finch", threads=[thread])
        self.assertEqual(assessment(pr)["group"], 3)
        thread["comments"].append(PEER)
        self.assertEqual(assessment(pr)["reasons"], ["Unanswered review thread"])
        thread["comments"].append({"login": "build", "bot": True})
        self.assertEqual(assessment(pr)["group"], 0)
        self.assertEqual(assessment(pr, bots=["LARK"])["group"], 3)
        thread["resolved"] = True
        self.assertEqual(assessment(pr)["group"], 3)

    def test_changes_requested_precedence_and_bots(self):
        changed = review(PEER, "CHANGES_REQUESTED")
        own = pull(author="finch", reviews=[changed, review(PEER, "COMMENTED")])
        self.assertEqual(assessment(own)["reasons"], ["Changes requested"])
        self.assertEqual(assessment(own, bots=["LARK"])["group"], 3)
        own["reviews"].append(review(PEER, "APPROVED"))
        self.assertEqual(assessment(own)["group"], 3)
        other = pull(requests=["FINCH"], reviews=[changed])
        self.assertEqual(assessment(other)["group"], 3)
        self.assertEqual(assessment(other, while_changes_requested=True)["group"], 1)
        self.assertEqual(assessment(other, bots=["LARK"])["group"], 1)

    def test_direct_and_team_request_modes(self):
        pr = pull(team_requests=[TEAM])
        self.assertEqual(assessment(pr)["group"], 1)
        self.assertEqual(assessment(pr, team_requests="never")["group"], 3)
        for ignored in (TEAM.upper(), "editors"):
            self.assertEqual(assessment(pr, ignore_teams=[ignored])["group"], 3)
        pr["reviews"] = [review(SELF, "PENDING")]
        self.assertEqual(assessment(pr)["group"], 1)
        pr["reviews"] = [review(SELF, "COMMENTED")]
        self.assertEqual(assessment(pr)["group"], 3)
        self.assertEqual(assessment(pr, team_requests="always")["group"], 1)
        pr["requests"] = ["finch"]
        self.assertEqual(assessment(pr, team_requests="never")["reasons"], ["Review requested again"])
        self.assertEqual(classifier.classify(pull(team_requests=[TEAM]), "finch")["group"], 3)

    def test_pending_review_by_someone_else(self):
        pr = pull(requests=["finch"], reviews=[review(PEER, "PENDING")])
        self.assertEqual(assessment(pr)["reasons"], ["Another reviewer is reviewing"])
        self.assertEqual(assessment(pr, while_reviewing=True)["group"], 1)
        self.assertEqual(assessment(pr, bots=["lark"])["group"], 1)

    def test_fyi_switches_and_precedence(self):
        cases = [
            ("commits_after_feedback", "New commits since your review", {"reviews": [review(SELF, "COMMENTED")]}),
            ("commits_after_feedback", "New commits since your review",
             {"reviews": [review(SELF, "CHANGES_REQUESTED")]}),
            ("commits_after_approval", "New commits since your review", {"reviews": [review(SELF, "APPROVED")]}),
            ("dismissed", "Your review was dismissed", {"reviews": [review(SELF, "DISMISSED")]}),
            ("replies", "Reply in your review thread", {"threads": [{"resolved": False, "comments": [SELF, PEER]}]}),
        ]
        for setting, reason, fields in cases:
            with self.subTest(setting=setting, fields=fields):
                pr = pull(**fields)
                self.assertEqual(assessment(pr)["group"], 3)
                self.assertEqual(assessment(pr, **{setting: True})["reasons"], [reason])
                self.assertEqual(assessment(pr, **{setting: True})["group"], 2)
                pr["requests"] = ["finch"]
                self.assertEqual(assessment(pr, **{setting: True})["group"], 1)
        self.assertEqual(assessment(pull(head="abc", reviews=[review(SELF, "APPROVED")]),
                                    commits_after_approval=True)["group"], 3)
        thread = {"resolved": False, "comments": [SELF, PEER]}
        self.assertEqual(assessment(pull(threads=[thread]), replies=True, bots=["lark"])["group"], 3)

    def test_row_details_follow_current_human_reviews_and_eligible_requests(self):
        thread = {"resolved": False, "comments": [PEER]}
        own = pull(author="finch", threads=[thread, thread, {**thread, "resolved": True}],
                   reviews=[review(PEER, "CHANGES_REQUESTED")])
        self.assertEqual(assessment(own)["details"], {"unanswered": 2, "changes_by": ["lark"]})

        event = {"since": "2026-11-23T10:00:00Z", "by": "lark"}
        other = pull(reviews=[review(SELF, "APPROVED")], requests=["finch"],
                     review_requested={"finch": event, "unrelated": {**event, "by": "owl"}})
        self.assertEqual(assessment(other)["details"],
                         {"requested_by": "lark", "requested_at": event["since"]})

    def test_waiting_age_survives_updates_and_resets_after_leaving_queue(self):
        options = {**storage.DEFAULT_SETTINGS, "notifications": False}
        pr = pull(author="finch", ci="FAILURE")
        state = {}
        cache = {"login": "finch", "status": "ok", "pulls": {pr["id"]: pr}}

        def project(now, **changes):
            pr.update(changes)
            summary, alerts = service.project(ACCOUNT, cache, options, state, now)
            self.assertEqual(alerts, [])
            return summary["rows"][0]

        initial = project(100)["waiting_since"]
        self.assertEqual(project(200, updated="2026-11-24T14:00:00Z")["waiting_since"], initial)
        self.assertEqual(project(300, ci="PENDING")["group"], 3)
        self.assertEqual(project(400, ci="FAILURE")["waiting_since"], "1970-01-01T00:06:40Z")

    def test_notification_seed_and_deduplication(self):
        database = {}
        pr = pull(requests=["finch"])
        cache = {"login": "finch", "status": "ok", "pulls": {pr["id"]: pr}}
        summary, alerts = service.project(ACCOUNT, cache, storage.DEFAULT_SETTINGS, database, 100)
        self.assertEqual((summary["count"], alerts), (1, []))
        self.assertEqual(service.project(ACCOUNT, cache, storage.DEFAULT_SETTINGS, database, 200)[1], [])
        pr["requests"] = []
        service.project(ACCOUNT, cache, storage.DEFAULT_SETTINGS, database, 300)
        pr["requests"] = ["finch"]
        alerts = service.project(ACCOUNT, cache, storage.DEFAULT_SETTINGS, database, 400)[1]
        self.assertEqual(alerts, [(pr["url"], "Studio", "finch", "Review requested")])
        self.assertEqual(service.project(ACCOUNT, cache, storage.DEFAULT_SETTINGS, database, 500)[1], [])


class PollingTests(unittest.TestCase):
    def test_legacy_snoozes_are_dropped_and_prs_count_again(self):
        pr = pull(requests=["finch"])
        identifier = ACCOUNT["id"]
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(service, "STATE", Path(folder)), \
             patch.object(service, "accounts", return_value=[ACCOUNT]), \
             patch.object(service, "settings", return_value=storage.DEFAULT_SETTINGS), \
             patch.object(service.subprocess, "Popen") as launch:
            state_path = Path(folder) / "state.json"
            history = {pr["id"]: [1, ["Review requested"]]}
            storage.atomic(state_path, {identifier: {
                "identity": [ACCOUNT["host"], "finch"], "seeded": True, "history": history,
                "snoozes": {pr["id"]: {"until": 9_999_999_999}},
            }})
            radar = service.Radar()
            self.assertNotIn("snoozes", radar.state[identifier])
            radar.cache = {identifier: {"login": "finch", "status": "ok", "pulls": {pr["id"]: pr}}}
            radar.update()
            self.assertEqual(radar.snapshot["count"], 1)
            self.assertNotIn("snoozes", storage.read_json(state_path, {})[identifier])
            self.assertEqual(radar.state[identifier]["history"], history)
            launch.assert_not_called()

    def test_rate_limited_account_does_not_reschedule_healthy_accounts(self):
        other = {"id": "b" * 32, "host": "github.com", "label": "Community"}
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(service, "STATE", Path(folder)), \
             patch.object(service, "settings", return_value=storage.DEFAULT_SETTINGS), \
             patch.object(service, "accounts", return_value=[ACCOUNT, other]), \
             patch.object(service.time, "time", return_value=1000), \
             patch.object(service, "refresh", return_value={"host": ACCOUNT["host"], "status": "loading"}) as refresh:
            radar = service.Radar()
            radar.cache = {
                ACCOUNT["id"]: {"host": ACCOUNT["host"], "next_at": 1000, "reset": 1000},
                other["id"]: {"host": other["host"], "next_at": 1170},
            }
            with patch.object(service, "atomic", wraps=storage.atomic) as write:
                radar.update(poll=True)
            projections = [call.args[1] for call in write.call_args_list
                           if call.args[0].name == "snapshot.json"]
            self.assertEqual([projection["refreshing"] for projection in projections], [True, False])
            self.assertEqual(refresh.call_count, 1)
            self.assertEqual(refresh.call_args.args[0], ACCOUNT)
            self.assertEqual(radar.next_poll(), 1170)
            self.assertEqual([account["label"] for account in radar.snapshot["accounts"]],
                             ["Studio", "Community"])

    def test_selected_account_persists_locally_and_rejects_unknown_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            with patch.object(service, "STATE", state), \
                 patch.object(service, "settings", return_value=storage.DEFAULT_SETTINGS), \
                 patch.object(service, "accounts", return_value=[ACCOUNT]):
                radar = service.Radar()
                radar.update()
                radar.handle({"operation": "select-account", "account": "unknown"})
                self.assertFalse(radar.selection_path.exists())
                radar.handle({"operation": "select-account", "account": ACCOUNT["id"]})
                self.assertEqual(storage.read_json(state / "snapshot.json", {})["selected_account"], ACCOUNT["id"])
                restarted = service.Radar()
                restarted.update()
                self.assertEqual(restarted.snapshot["selected_account"], ACCOUNT["id"])

    def test_repository_selection_persists_per_account_and_clears_when_empty(self):
        other = {**ACCOUNT, "id": "b" * 32}
        first = pull(requests=["finch"])
        second = pull(repo="finch/notes", requests=["finch"])
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(service, "STATE", Path(folder)), \
             patch.object(service, "settings", return_value=storage.DEFAULT_SETTINGS), \
             patch.object(service, "accounts", return_value=[ACCOUNT, other]):
            cache = {account["id"]: {"status": "ok", "login": "finch", "pulls": {pr["id"]: pr}}
                     for account, pr in [(ACCOUNT, first), (other, second)]}
            radar = service.Radar()
            radar.cache = cache
            radar.update()
            for account, pr in [(ACCOUNT, first), (other, second)]:
                radar.handle({"operation": "select-repository", "account": account["id"], "repository": pr["repo"]})
            radar.handle({"operation": "select-repository", "account": other["id"], "repository": first["repo"]})
            self.assertEqual(radar.snapshot["count"], 2)

            restarted = service.Radar()
            restarted.cache = cache
            restarted.update()
            self.assertEqual(restarted.snapshot["selected_repositories"],
                             {ACCOUNT["id"]: first["repo"], other["id"]: second["repo"]})
            cache[ACCOUNT["id"]]["pulls"] = {}
            restarted.update()
            self.assertEqual(restarted.snapshot["selected_repositories"], {other["id"]: second["repo"]})
            restarted.handle({"operation": "select-repository", "account": other["id"], "repository": ""})
            self.assertEqual(service.Radar().selected_repositories, {})

    def test_incremental_owner_filter_and_manual_full_refresh(self):
        api = Mock()
        api.identity.return_value = "finch"
        api.teams.return_value = [TEAM]
        first = pull()
        second = pull(id="pr-2", number=9)
        outside = pull(id="pr-3", repo="violet-heron/notes")
        api.search.return_value = [{"id": pr["id"], "updatedAt": pr["updated"],
                                    "repository": {"nameWithOwner": pr["repo"]}}
                                   for pr in (first, second, outside)]
        api.details.side_effect = lambda identifiers, login: [
            pr for pr in (first, second, outside) if pr["id"] in identifiers]
        options = {**storage.DEFAULT_SETTINGS, "owners": {ACCOUNT["id"]: ["Paper-Finch"]}}
        apply = lambda current, now, force=False: service.refresh(ACCOUNT, current, options, now, force,
                                                                   client_factory=lambda account: api)
        cache = apply({}, 100)
        self.assertEqual(set(cache["pulls"]), {"pr-1", "pr-2"})
        api.details.assert_called_with(["pr-1", "pr-2"], "finch")
        api.search.return_value[0]["updatedAt"] = "2026-11-23T21:00:00Z"
        cache = apply(cache, 400)
        api.details.assert_called_with(["pr-1"], "finch")
        cache = apply(cache, 700, True)
        api.details.assert_called_with(["pr-1", "pr-2"], "finch")
        self.assertEqual(api.teams.call_count, 1)
        apply(cache, 4300)
        self.assertEqual(api.teams.call_count, 2)
        api.details.assert_called_with(["pr-1", "pr-2"], "finch")

    def test_rate_limit_preserves_cache_and_blocks_manual_poll(self):
        api = Mock()
        api.search.side_effect = client.RateLimited(900)
        cache = {"login": "finch", "host": ACCOUNT["host"], "identity_at": 100, "teams": [],
                 "teams_at": 100, "pulls": {"pr-1": pull()}}
        factory = Mock(return_value=api)
        limited = service.refresh(ACCOUNT, cache, storage.DEFAULT_SETTINGS, 500, client_factory=factory)
        self.assertEqual((limited["status"], limited["reset"]), ("rate-limited", 900))
        self.assertEqual(limited["pulls"], cache["pulls"])
        self.assertEqual(service.refresh(ACCOUNT, limited, storage.DEFAULT_SETTINGS, 800, True, factory), limited)
        factory.assert_called_once_with(ACCOUNT)

    def test_gh_headers_and_environment_are_account_scoped(self):
        def response(code=0, body="{}", stderr="", headers=""):
            return subprocess.CompletedProcess([], code, "HTTP/2.0 200 OK\r\n" + headers
                                               + "\r\n\r\n" + body, stderr)

        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                "XDG_CONFIG_HOME": folder, "GH_TOKEN": "fixture", "GITHUB_TOKEN": "fixture",
                "GH_ENTERPRISE_TOKEN": "fixture", "GH_HOST": "outside.invalid",
                "GH_CONFIG_DIR": "/outside", "GH_DEBUG": "api"}):
            runner = Mock(return_value=response(body='{"login":"finch"}'))
            self.assertEqual(client.GitHub(ACCOUNT, runner).identity(), "finch")
            invocation = runner.call_args
            env = invocation.kwargs["env"]
            self.assertEqual(env["GH_CONFIG_DIR"], str(Path(folder) / "eitr/git-accounts/cli" / ACCOUNT["id"]))
            self.assertEqual(env["GH_HOST"], "github.com")
            self.assertFalse(env.keys() & {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GH_DEBUG"})
            runner.return_value = response(code=1, stderr="gh auth login")
            signed_out = service.refresh(ACCOUNT, {}, storage.DEFAULT_SETTINGS, 10,
                                         client_factory=lambda account: client.GitHub(account, runner))
            self.assertEqual(signed_out["status"], "signed-out")
            runner.return_value = response(code=1, stderr="HTTP 429", headers="Retry-After: 125")
            with patch.object(client.time, "time", return_value=10), self.assertRaises(client.RateLimited) as caught:
                client.GitHub(ACCOUNT, runner).identity()
            self.assertEqual(caught.exception.reset, 135)

    def test_search_runs_one_query_per_involvement_and_merges(self):
        # GitHub search returns nothing for parenthesised OR between qualifiers.
        pages = {"involves": [{"id": "a"}, {"id": "b"}], "review-requested": [{"id": "b"}, {"id": "c"}],
                 "reviewed-by": [{"id": "a"}]}
        queries = []
        def graphql(query, search, cursor):
            queries.append(search)
            self.assertNotIn(" OR ", search)
            kind = next(name for name in pages if f"{name}:finch" in search)
            return {"search": {"nodes": pages[kind], "pageInfo": {"hasNextPage": False, "endCursor": None}}}
        github = client.GitHub(ACCOUNT, Mock())
        github.graphql = graphql
        self.assertEqual([node["id"] for node in github.search("finch")], ["a", "b", "c"])
        self.assertEqual(len(queries), 3)

    def test_graphql_sends_variables_on_stdin_and_normalizes_pull(self):
        raw = {"id": "pr-1", "state": "OPEN", "number": 2, "url": pull()["url"], "title": "Guide",
               "updatedAt": "2026-11-23", "createdAt": "2026-11-22", "isDraft": False,
               "headRefOid": "def", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY",
               "reviewDecision": "CHANGES_REQUESTED", "author": None,
               "repository": {"nameWithOwner": "paper-finch/books"},
               "statusCheckRollup": {"state": "FAILURE"},
               "reviews": {"nodes": [{"id": "review-1", "state": "APPROVED", "author": PEER, "commit": {"oid": "def"}}]},
               "reviewRequests": {"nodes": [{"requestedReviewer": SELF}]},
               "timelineItems": {"nodes": [
                   {"requestedReviewer": SELF, "createdAt": "2026-11-21T10:00:00Z", "actor": None},
                   {"requestedReviewer": SELF, "createdAt": "2026-11-22T10:00:00Z", "actor": PEER},
               ]},
               "reviewThreads": {"nodes": []}}
        completed = subprocess.CompletedProcess([], 0, json.dumps({"data": {"nodes": [raw]}}), "")
        runner = Mock(return_value=completed)
        [row] = list(client.GitHub(ACCOUNT, runner).details(["pr-1"], "finch"))
        self.assertEqual((row["ci"], row["requests"], row["conflict"]), ("FAILURE", ["finch"], True))
        self.assertEqual(row["review_requested"], {"finch": {"since": "2026-11-22T10:00:00Z", "by": "lark"}})
        self.assertEqual(json.loads(runner.call_args.kwargs["input"])["variables"], {"ids": ["pr-1"], "login": "finch"})

    def test_collapsed_sections_are_validated_and_round_trip(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(storage, "CONFIG", Path(folder) / "github.json"):
            self.assertEqual(storage.settings()["collapsed_sections"], ["fyi", "waiting"])
            storage.atomic(storage.CONFIG, {"collapsed_sections": ["own", "snoozed", "own", "waiting"],
                                            "destination": "off", "reviews_folder": "/unused"})
            options = storage.settings()
            self.assertEqual(options["collapsed_sections"], ["own", "waiting"])
            self.assertNotIn("destination", options)
            self.assertNotIn("reviews_folder", options)
            storage.atomic(storage.CONFIG, {"collapsed_sections": ["unknown"]})
            self.assertEqual(storage.settings()["collapsed_sections"], ["fyi", "waiting"])

    def test_translation_catalog_covers_every_locale_and_notification_reason(self):
        catalog = (PLUGIN / "Strings.js").read_text().split("var translations = ", 1)[1].split(";\n", 1)[0]
        messages = json.loads(catalog)
        self.assertTrue(all(len(versions) == 7 and all(versions) for versions in messages.values()))
        with patch.dict(os.environ, {"LC_ALL": "pt_BR.UTF-8"}):
            self.assertEqual(actions.translated("Review requested"), "Revisão solicitada")
