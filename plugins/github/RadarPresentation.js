.pragma library
.import "Strings.js" as Strings

function repositories(rows) {
    const entries = new Map();
    const shortNames = new Map();
    for (const pr of rows) {
        if (!entries.has(pr.repo)) {
            const shortName = pr.repo.split("/").pop();
            entries.set(pr.repo, {name: pr.repo, label: shortName, count: 0});
            shortNames.set(shortName.toLowerCase(), (shortNames.get(shortName.toLowerCase()) || 0) + 1);
        }
        if (!pr.draft && pr.group < 2)
            entries.get(pr.repo).count++;
    }
    const repos = Array.from(entries.values());
    for (const repo of repos) {
        if (shortNames.get(repo.label.toLowerCase()) > 1)
            repo.label = repo.name;
    }
    return repos.sort((left, right) => right.count - left.count
        || left.name.split("/").pop().localeCompare(right.name.split("/").pop())
        || left.name.localeCompare(right.name));
}

function age(timestamp, now) {
    const minutes = Math.max(0, Math.floor((now - timestamp) / 60000));
    if (minutes < 60) return Strings.tr("%1m").replace("%1", minutes);
    if (minutes < 1440) return Strings.tr("%1h").replace("%1", Math.floor(minutes / 60));
    return Strings.tr("%1d").replace("%1", Math.floor(minutes / 1440));
}

function reasons(pr) {
    const details = pr.details || {};
    return pr.reasons.map(reason => {
        if (reason === "Unanswered review thread" && details.unanswered > 1)
            return Strings.tr("%1 unanswered threads").replace("%1", details.unanswered);
        if (reason === "Changes requested" && details.changes_by && details.changes_by.length)
            return Strings.tr("Changes requested by %1").replace("%1", details.changes_by.join(", "));
        if (reason === "Review requested again" && details.requested_by)
            return Strings.tr("Re-requested by %1").replace("%1", details.requested_by);
        return Strings.tr(reason === "Merge conflict" ? "Conflict" : reason);
    }).concat(pr.conflict && !pr.reasons.includes("Merge conflict") ? [Strings.tr("Conflict")] : []);
}

function reviewers(pr) {
    const states = new Map();
    for (const review of pr.reviews) {
        const previous = states.get(review.login);
        if (review.state !== "COMMENTED" || !previous)
            states.set(review.login, review.state);
    }
    for (const login of pr.requests.concat(pr.team_requests))
        states.set(login, "Requested");
    return Array.from(states, ([login, state]) => ({login: login, state: state}));
}

function reviewerState(state) {
    if (state === "APPROVED") return {glyph: "\u{F00C}", key: "color2"};
    if (state === "CHANGES_REQUESTED") return {glyph: "\u{F00D}", key: "color1"};
    if (state === "COMMENTED") return {glyph: "\u{F075}", key: ""};
    if (state === "PENDING" || state === "Requested") return {glyph: "\u{F017}", key: "color3"};
    return {glyph: "\u{F068}", key: ""};
}

// One status for the row's trailing icon, drawn as a person (reviews are people): what blocks or
// clears the merge, most urgent first.
function reviewStatus(pr) {
    if (pr.conflict) return {glyph: "\u{F071}", key: "color3", label: "Merge conflict"};
    const states = reviewers(pr).map(reviewer => reviewer.state);
    if (pr.decision === "CHANGES_REQUESTED" || states.includes("CHANGES_REQUESTED"))
        return {glyph: "\u{F12DF}", key: "color1", label: "Changes requested"};
    if (pr.decision === "APPROVED" || (!pr.decision && states.includes("APPROVED")))
        return {glyph: "\u{F0008}", key: "color2", label: "Approved"};
    if (states.includes("Requested") || states.includes("PENDING") || pr.decision === "REVIEW_REQUIRED")
        return {glyph: "\u{F0B56}", key: "", label: "Review required"};
    if (states.includes("COMMENTED")) return {glyph: "\u{F086}", key: "", label: "Commented"};
    return null;
}

// CI is a status light (a dot), so it never reads like a review's check mark.
function ciState(state) {
    if (state === "SUCCESS") return {glyph: "\u{F0765}", key: "color2"};
    if (state === "FAILURE" || state === "ERROR") return {glyph: "\u{F0765}", key: "color1"};
    if (state === "PENDING" || state === "EXPECTED") return {glyph: "\u{F0765}", key: "color3"};
    return {glyph: "\u{F0766}", key: ""};
}

function tone(api, key) {
    const color = key === "accent" ? api.accent : key && api.palette ? api.palette[key] : null;
    if (!color) return api.foreground;
    const luminance = value => {
        const linear = channel => channel <= 0.04045 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4);
        return 0.2126 * linear(value.r) + 0.7152 * linear(value.g) + 0.0722 * linear(value.b);
    };
    const surface = luminance(api.background);
    for (let step = 0; step <= 10; step++) {
        const ink = Qt.tint(color, Qt.alpha(api.foreground, step / 10));
        const value = luminance(ink);
        if ((Math.max(surface, value) + 0.05) / (Math.min(surface, value) + 0.05) >= 4.5)
            return ink;
    }
    return api.foreground;
}
