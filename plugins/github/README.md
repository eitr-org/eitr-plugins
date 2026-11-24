# GitHub PR radar

Click the GitHub icon on the left of the desktop bar or open **GitHub: Your
move** in Walker. The header’s **Account** selector shows each account’s label,
GitHub login and **your move** count. The selection is saved on this machine.
By default the first account with **your move** items opens, or the first
account if none has items. The bar badge sums the first two groups across
accounts and excludes drafts. It shows up to **99+** and is hidden
when the glyph is muted. Older Eitr versions show the count beside the glyph.
Use **Refresh** or **Ctrl+R** for an immediate refresh when GitHub allows it.

Choose **All** in the **Repository** dropdown to see the selected account’s PRs
with repository headings in each group. Choose a repository to see just its
PRs. The dropdown shows each repository’s **your move** count, highest first,
with alphabetical ordering for ties. Repositories that share a short name also
show their owner. Each account remembers its own selection on this machine and
returns to **All** when the chosen repository no longer has PRs.

The two **your move** groups start expanded. **FYI** and **Waiting**
start collapsed. Section choices are remembered on this machine and apply across
tabs. The actionable queue puts PRs that have been waiting longest first. The
other groups show the most recently updated PRs first. If a PR is already
actionable when first seen, the radar uses the PR's last update as an estimate
when it lacks a review-request timestamp.

Click a row or press Enter or Space while it has focus to open the PR in your
browser. The review status icon leads the row and the CI light sits at the right
edge. Reviewer initials and reason chips show details on hover.

The radar uses the GitHub profiles already set up in **Git Accounts**. Sign in
there for any account marked **Log in through Git Accounts**. In the radar's
**Settings**, enter comma-separated repository owners for each account. Leave
the list empty to include all owners in that account's results.

## Rules

| Group or setting | Default | Behavior |
|---|---|---|
| Your PRs: your move | On | Unanswered, current human review threads and outstanding change requests need attention. |
| Approved and ready | On | GitHub reports approved, green checks and a clean merge state. Turning the setting off sends this reason to FYI. |
| CI failure | On | Failed or errored CI on your PR needs attention. Turning the setting off sends this reason to FYI. |
| Merge conflict | On | A conflict on your PR needs attention. Turning the setting off sends this reason to FYI. |
| Others’ PRs: your move | On | An explicit review request counts, including a request after a submitted review. |
| Team requests | Until I review | Count while requested and before your first submitted review. Choose Always or Never in Settings. |
| Ignored teams | Empty | Exclude team requests by `owner/team` or by team slug. Explicit individual requests still apply. |
| Requested while changes are open | Off | Group under Waiting while another reviewer has an outstanding change request. |
| Requested while another review is in progress | Off | Group under Waiting when GitHub returns another reviewer's pending review. |
| New commits after comments or requested changes | Off | Show in FYI when the head differs from your last commented or changes-requested review. |
| New commits after approval | Off | Show in FYI when the head differs from the head you approved. |
| Replies in your review threads | Off | Show in FYI when a human has the latest reply in a thread you started. |
| Dismissed review | Off | Show in FYI when your latest review was dismissed. |
| Treat as bots | Empty | Exclude reviews and replies from these comma-separated logins and actors GitHub identifies as bots. |
| Waiting | On | Remaining PRs and drafts. |

The first successful load for an account seeds its state silently. Subsequent
moves into an actionable state produce one notification per account and PR with
the reason. Clicking the notification opens the PR. Turn alerts off under
**Settings → Notifications**.

## Background service and storage

The five-minute background GitHub check keeps desktop notifications working
while the bar item and panel are closed. The panel and bar watch a local JSON
snapshot. The service uses a GraphQL search per account, with additional pages
as needed, and fetches detail only for new or updated PRs on incremental runs.
It refreshes teams and cached PR details hourly. Manual refresh fetches full PR
details and respects GitHub's rate-limit reset. CI or mergeability changes can
take until the next full refresh if GitHub leaves the PR's update timestamp alone.
The available review activity and team membership depend on what GitHub exposes
to the active account and its existing authorization.

Preferences live in `$XDG_CONFIG_HOME/eitr/plugins/github.json`. The service
writes its snapshot, cached PRs, account and repository selections and
notification history under
`$XDG_STATE_HOME/eitr/plugins/github/` using atomic replacement. These files
can contain PR metadata from private repositories. GitHub credentials stay in
each Git Accounts CLI profile.
