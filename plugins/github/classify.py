"""Pure PR classification and notification transitions."""

DEFAULTS = {
    "team_requests": "until-reviewed", "ignore_teams": [], "bots": [],
    "ready": True, "failure": True, "conflict": True,
    "commits_after_feedback": False, "commits_after_approval": False,
    "replies": False, "dismissed": False,
    "while_changes_requested": False, "while_reviewing": False,
}


def classify(pr, login, teams=(), options=None):
    options = {**DEFAULTS, **(options or {})}
    login = login.casefold()
    own = pr["author"].casefold() == login
    fyi = []
    details = {}

    def result(group, *reasons):
        return {"group": group, "reasons": list(reasons), "details": details}

    def human(actor):
        return actor and not actor.get("bot") and actor["login"].casefold() not in bots

    bots = {name.casefold() for name in options["bots"]}
    reviews = [review for review in pr.get("reviews", []) if human(review)]
    mine = [review for review in reviews if review["login"].casefold() == login
            and review["state"] != "PENDING"]
    reviewed = bool(mine)
    latest = {}
    feedback = {}
    for review in reviews:
        reviewer = review["login"].casefold()
        latest[reviewer] = review
        if review["state"] in {"CHANGES_REQUESTED", "APPROVED", "DISMISSED"}:
            feedback[reviewer] = review
    change_requests = [review["login"] for reviewer, review in feedback.items()
                       if review["state"] == "CHANGES_REQUESTED" and reviewer != login]

    if pr.get("draft"):
        return result(3, "Draft")

    threads = [thread for thread in pr.get("threads", []) if thread["comments"]]
    if own:
        reasons = []
        unanswered = []
        for thread in threads:
            last = next((comment for comment in reversed(thread["comments"]) if human(comment)), None)
            if (not thread["resolved"] and not thread.get("outdated")
                    and last and last["login"].casefold() != login):
                unanswered.append(last)
        if unanswered:
            reasons.append("Unanswered review thread")
            details["unanswered"] = len(unanswered)
        if change_requests:
            details["changes_by"] = change_requests
            reasons.append("Changes requested")
        ready = (pr.get("decision") == "APPROVED" and pr["ci"] == "SUCCESS"
                 and pr.get("merge") == "CLEAN")
        for active, setting, reason in (
            (pr.get("conflict"), "conflict", "Merge conflict"),
            (pr["ci"] in {"FAILURE", "ERROR"}, "failure", "CI failed"),
            (ready, "ready", "Ready to merge"),
        ):
            if active:
                (reasons if options[setting] else fyi).append(reason)
        if reasons:
            return result(0, *reasons)
        return result(2, *fyi) if fyi else result(3, "Waiting for reviewers or CI")

    requested = login in {name.casefold() for name in pr.get("requests", [])}
    ignored = {team.casefold() for team in options["ignore_teams"]}
    eligible = {team.casefold() for team in teams} - ignored
    mode = options["team_requests"]
    targets = [login] if requested else []
    if mode == "always" or (mode == "until-reviewed" and not reviewed):
        targets.extend(team.casefold() for team in pr.get("team_requests", [])
                       if team.casefold() in eligible and team.split("/")[-1].casefold() not in ignored)
    if targets:
        if change_requests and not options["while_changes_requested"]:
            return result(3, "Waiting on the author")
        if not options["while_reviewing"] and any(
            reviewer != login and review["state"] == "PENDING"
            for reviewer, review in latest.items()
        ):
            return result(3, "Another reviewer is reviewing")
        events = pr.get("review_requested", {})
        request = min((events[target] for target in targets if target in events),
                      key=lambda event: event["since"], default=None)
        if request:
            details["requested_by"] = request["by"]
            details["requested_at"] = request["since"]
        return result(1, "Review requested again" if reviewed else "Review requested")

    if mine:
        last = mine[-1]
        if last["state"] == "DISMISSED" and options["dismissed"]:
            fyi.append("Your review was dismissed")
        changed = last.get("commit") and last["commit"] != pr.get("head")
        if changed and (
            (last["state"] == "APPROVED" and options["commits_after_approval"])
            or (last["state"] in {"COMMENTED", "CHANGES_REQUESTED"}
                and options["commits_after_feedback"])
        ):
            fyi.append("New commits since your review")
    if options["replies"]:
        for thread in threads:
            comments = thread["comments"]
            last = next((comment for comment in reversed(comments) if human(comment)), None)
            if (comments[0] and comments[0]["login"].casefold() == login
                    and last and last["login"].casefold() != login):
                fyi.append("Reply in your review thread")
                break
    return result(2, *fyi) if fyi else result(3, "Waiting on the author")


def notification(previous, assessment, seeded):
    group = assessment["group"]
    state = [group, assessment["reasons"]]
    alert = seeded and group < 2 and previous != state
    return state, alert
