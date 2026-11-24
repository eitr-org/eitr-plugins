"""Read-only GitHub client using the Git Accounts CLI profile for each account."""
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import subprocess
import time


class Unavailable(Exception):
    pass


class SignedOut(Unavailable):
    pass


class RateLimited(Unavailable):
    def __init__(self, reset):
        self.reset = reset


def config_root():
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "eitr"


def read_json(path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def accounts():
    model = read_json(config_root() / "git-accounts.json", {})
    return sorted(
        (dict(account, id=identifier) for identifier, account in model.get("accounts", {}).items()
         if account.get("provider") == "github" and re.fullmatch(r"[a-f0-9]{32}", identifier)
         and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*", account.get("host", ""))),
        key=lambda account: account["label"].casefold(),
    )


def environment(account):
    env = dict(os.environ)
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN",
                 "GITHUB_ENTERPRISE_TOKEN", "GH_HOST", "GH_CONFIG_DIR",
                 "GH_DEBUG", "DEBUG", "GH_FORCE_TTY"):
        env.pop(name, None)
    directory = config_root() / "git-accounts" / "cli" / account["id"]
    env.update(GH_CONFIG_DIR=str(directory), GH_HOST=account["host"], GH_PROMPT_DISABLED="1",
               GH_NO_UPDATE_NOTIFIER="1", GH_NO_EXTENSION_UPDATE_NOTIFIER="1")
    return env


def chunks(values, size):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def rate_reset(headers, errors, stderr):
    limited = ("rate limit" in stderr.lower() or "HTTP 429" in stderr
               or headers.get("x-ratelimit-remaining") == "0"
               or any(error.get("type") == "RATE_LIMITED" for error in errors))
    if not limited and "retry-after" not in headers:
        return None
    now = time.time()
    if "retry-after" in headers:
        value = headers["retry-after"]
        try:
            return max(now + 1, now + int(value))
        except ValueError:
            try:
                return max(now + 1, parsedate_to_datetime(value).timestamp())
            except (ValueError, TypeError, OverflowError):
                pass
    try:
        return max(now + 1, int(headers["x-ratelimit-reset"]))
    except (KeyError, ValueError):
        return now + 300


class GitHub:
    def __init__(self, account, runner=subprocess.run):
        self.account = account
        self.env = environment(account)
        self.runner = runner

    def request(self, endpoint, *args, payload=None):
        if payload is not None:
            args = (*args, "--method", "POST", "--input", "-")
        try:
            process = self.runner(
                ["gh", "api", "--hostname", self.account["host"], "--include", endpoint, *args],
                capture_output=True, text=True, timeout=15, env=self.env, cwd="/",
                input=json.dumps(payload) if payload is not None else None,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError):
            raise Unavailable from None
        header, separator, body = process.stdout.replace("\r\n", "\n").partition("\n\n")
        if not separator or not header.startswith("HTTP/"):
            body, header = process.stdout, ""
        headers = {line.split(":", 1)[0].lower(): line.split(":", 1)[1].strip()
                   for line in header.splitlines()[1:] if ":" in line and not line[:1].isspace()}
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        errors = payload.get("errors", []) if isinstance(payload, dict) else []
        reset = rate_reset(headers, errors or [], process.stderr)
        if reset and (process.returncode or errors):
            raise RateLimited(reset)
        if ("HTTP 401" in process.stderr or "gh auth login" in process.stderr
                or re.match(r"HTTP/\S+ 401\b", header)):
            raise SignedOut
        if process.returncode or payload is None or errors:
            raise Unavailable
        return payload, headers

    def graphql(self, query, **variables):
        payload, _headers = self.request("graphql", payload={"query": query, "variables": variables})
        if not payload.get("data"):
            raise Unavailable
        return payload["data"]

    def identity(self):
        return self.request("user")[0]["login"]

    def teams(self):
        teams = []
        for page in range(1, 11):
            rows, headers = self.request(f"user/teams?per_page=100&page={page}")
            teams.extend(team["organization"]["login"] + "/" + team["slug"] for team in rows)
            if 'rel="next"' not in headers.get("link", ""):
                break
        return teams

    def search(self, login):
        # GitHub search ignores parenthesised OR between qualifiers, so each kind of
        # involvement is its own query; review-requested also covers team requests.
        seen = set()
        for qualifier in ("involves", "review-requested", "reviewed-by"):
            query = f"is:pr is:open archived:false {qualifier}:{login} sort:updated-desc"
            cursor = None
            for _page in range(10):
                result = self.graphql(SEARCH, search=query, cursor=cursor)["search"]
                for node in result["nodes"]:
                    if node and node["id"] not in seen:
                        seen.add(node["id"])
                        yield node
                if not result["pageInfo"]["hasNextPage"]:
                    break
                cursor = result["pageInfo"]["endCursor"]

    def details(self, identifiers, login):
        for batch in chunks(identifiers, 12):
            for pr in self.graphql(DETAILS, ids=batch, login=login)["nodes"]:
                if pr and pr.get("state") == "OPEN":
                    yield normalize(pr)


SEARCH = """
query($search: String!, $cursor: String) {
 search(query: $search, type: ISSUE, first: 100, after: $cursor) {
  pageInfo { hasNextPage endCursor }
  nodes { ... on PullRequest { id updatedAt repository { nameWithOwner } } }
 }
}
"""

DETAILS = """
query($ids: [ID!]!, $login: String!) {
 nodes(ids: $ids) { ... on PullRequest {
  id state url number title updatedAt createdAt isDraft headRefOid mergeable mergeStateStatus reviewDecision
  author { login __typename } repository { nameWithOwner }
  statusCheckRollup { state }
  reviews: latestReviews(first: 100) { nodes { ...ReviewDetails } }
  opinions: latestOpinionatedReviews(first: 100) { nodes { ...ReviewDetails } }
  pending: reviews(last: 100, states: [PENDING]) { nodes { ...ReviewDetails } }
  ownReview: reviews(last: 1, author: $login, states: [APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED]) {
   nodes { ...ReviewDetails }
  }
  reviewRequests(first: 100) { nodes { requestedReviewer {
   ... on User { login }
   ... on Team { slug organization { login } }
  } } }
  timelineItems(last: 30, itemTypes: [REVIEW_REQUESTED_EVENT]) { nodes {
   ... on ReviewRequestedEvent { createdAt actor { login } requestedReviewer {
    ... on User { login }
    ... on Team { slug organization { login } }
   } }
  } }
  reviewThreads(first: 80) { nodes { isResolved isOutdated
   first: comments(first: 1) { nodes { id author { login __typename } } }
   last: comments(last: 10) { nodes { id author { login __typename } } }
  } }
 } }
}
fragment ReviewDetails on PullRequestReview {
 id state submittedAt author { login __typename } commit { oid }
}
"""

def actor(value):
    return {"login": value["login"], "bot": value.get("__typename") == "Bot"} if value else None


def nodes(value):
    return (value or {}).get("nodes") or []


def reviewer_name(reviewer):
    reviewer = reviewer or {}
    if "slug" in reviewer:
        return reviewer["organization"]["login"] + "/" + reviewer["slug"]
    return reviewer.get("login", "")


def normalize(pr):
    rollup = pr["statusCheckRollup"]
    distinct_reviews = {row["id"]: row for field in ("reviews", "opinions", "ownReview", "pending")
                        for row in nodes(pr.get(field))}
    ordered_reviews = sorted(distinct_reviews.values(),
                             key=lambda row: row.get("submittedAt") or "9999")
    reviews = [dict(author, state=row["state"], commit=(row.get("commit") or {}).get("oid"))
               for row in ordered_reviews if (author := actor(row["author"]))]
    requests, team_requests = [], []
    for row in nodes(pr["reviewRequests"]):
        reviewer = row["requestedReviewer"] or {}
        name = reviewer_name(reviewer)
        if name:
            (team_requests if "slug" in reviewer else requests).append(name)
    threads = [{"resolved": thread["isResolved"], "outdated": thread["isOutdated"],
                "comments": list({comment["id"]: actor(comment["author"]) for end in ("first", "last")
                                  for comment in nodes(thread.get(end))}.values())}
               for thread in nodes(pr["reviewThreads"])]
    return {
        "id": pr["id"], "url": pr["url"], "number": pr["number"], "title": pr["title"],
        "repo": pr["repository"]["nameWithOwner"], "author": (pr["author"] or {}).get("login", ""),
        "updated": pr["updatedAt"], "created": pr["createdAt"], "draft": pr["isDraft"],
        "head": pr["headRefOid"], "ci": (rollup or {}).get("state") or "NONE",
        "merge": pr["mergeStateStatus"], "conflict": pr["mergeable"] == "CONFLICTING",
        "decision": pr["reviewDecision"], "reviews": reviews, "requests": requests,
        "team_requests": team_requests, "threads": threads,
        "review_requested": {
            name.casefold(): {"since": event["createdAt"], "by": (event.get("actor") or {}).get("login", "")}
            for event in nodes(pr.get("timelineItems"))
            if (name := reviewer_name(event.get("requestedReviewer")))
        },
    }
