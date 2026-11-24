"""Render the radar with fixture accounts, PRs, and the native shared controls."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BAR = ROOT.parent / "eitr/quickshell/desktop-bar"
spec = importlib.util.spec_from_file_location("github_layout_render", BAR / "tests/layout_render.py")
rendering = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rendering)


def snapshot():
    def pull(number, title, account, group, reasons, **extra):
        return {
            "id": f"fixture-{number}", "number": number,
            "repo": "finch/atlas" if account == "personal" else "moss-quill/notes",
            "author": "gray-lark", "title": title, "updated": "2026-11-23T14:35:00Z",
            "reviews": [], "requests": [], "team_requests": [], "group": group,
            "ci": "SUCCESS", "reasons": reasons, **extra,
        }

    personal = [
        pull(18, "Document offline sync and restore", "personal", 0,
             ["Unanswered review thread", "CI failed"], author="tern", ci="FAILURE",
             details={"unanswered": 2}, waiting_since="2026-11-20T10:00:00Z",
             reviews=[{"login": "amber-moth", "state": "CHANGES_REQUESTED"},
                      {"login": "silver-wren", "state": "APPROVED"},
                      {"login": "gray-lark", "state": "COMMENTED"}],
             requests=["red-kite", "sand-piper"]),
        pull(25, "Keep exported dates in local time", "personal", 0, ["Ready to merge"],
             author="snow-tern", waiting_since="2026-11-23T10:00:00Z"),
        pull(32, "Try a smaller import preview", "personal", 1, ["Review requested"], ci="EXPECTED",
             requests=["snow-tern"]),
        pull(39, "Sketch a bulk move workflow", "personal", 3, ["Draft"], draft=True, ci="NONE"),
        pull(46, "Support plain-text exports", "personal", 1, ["Review requested"]),
    ]
    work = [
        pull(27, "Preserve note order when filtering", "work", 0, ["Changes requested"],
             details={"changes_by": ["wren"]}, author="violet-heron",
             waiting_since="2026-11-21T10:00:00Z",
             reviews=[{"login": "wren", "state": "CHANGES_REQUESTED"}, {"login": "gray-lark", "state": "APPROVED"},
                      {"login": "snow-tern", "state": "COMMENTED"}], requests=["amber-moth"]),
        pull(34, "Recover after an interrupted upload", "work", 0, ["CI failed", "Merge conflict"], ci="FAILURE", conflict=True,
             author="violet-heron", reviews=[{"login": "gray-lark", "state": "APPROVED"}]),
        pull(68, "Remember the last notebook on launch", "work", 1, ["Review requested again"],
             details={"requested_by": "gray-lark"}, requests=["violet-heron"],
             waiting_since="2026-11-22T10:00:00Z"),
        pull(71, "Skip empty attachment folders", "work", 1, ["Review requested"], ci="PENDING",
             requests=["violet-heron"]),
        pull(77, "Make archive links relative", "work", 1, ["Review requested"], ci="NONE",
             team_requests=["moss-quill/editors"]),
        pull(81, "Preserve tags during a notebook import", "work", 2, ["New commits since your review"]),
        pull(86, "Add sample notebooks", "work", 3, ["Waiting on the author"]),
    ]
    work.extend([
        pull(92, "Keep archive metadata on export", "work", 0, ["Ready to merge"]),
        pull(96, "Restore focus after a search", "work", 1, ["Review requested"], requests=["violet-heron"]),
        pull(102, "Show the active notebook in search", "work", 1, ["Review requested"], requests=["violet-heron"]),
        pull(108, "Keep saved filters in sync", "work", 2, ["New commits since your review"]),
        pull(111, "Move archived notes in batches", "work", 3, ["Waiting on the author"]),
    ])
    personal[2]["repo"] = "lark/atlas"
    personal[3]["repo"] = "finch/brush"
    personal[4]["repo"] = "finch/brush"
    for pr in personal + work:
        pr["url"] = f'https://github.com/{pr["repo"]}/pull/{pr["number"]}'
    return {
        "accounts": [
            {"id": "personal", "label": "Personal", "login": "snow-tern", "status": "ok", "count": 4,
             "rows": personal, "updated_at": 1795445100},
            {"id": "work", "label": "Work", "login": "violet-heron", "status": "ok", "count": 8,
             "rows": work, "updated_at": 1795445100},
        ],
        "count": 12, "options": {"ready": True, "failure": True, "conflict": True}, "updated_at": 1795445100,
    }


FIXTURE = '''import QtQuick
import QtTest
import QtQuick.Controls.Basic as Controls
import Quickshell
import "runtime" as Bar
import "github" as Plugin

ShellRoot {
    id: root
    property int step: 0
    property bool light: step >= 14
    property int shot: step % 14
    property var sample: SNAPSHOT
    property var manyRepos: {
        const account = sample.accounts[0];
        const extras = ["almanac", "canvas", "daybook", "etchings", "field-guide", "garden",
            "harbor", "inkstone", "journal", "keepsakes", "ledger", "mosaic"].map((name, index) =>
            Object.assign({}, account.rows[3], {id: "extra-" + index, repo: "finch/" + name}));
        return Object.assign({}, sample, {accounts: [Object.assign({}, account, {rows: account.rows.concat(extras)}),
            sample.accounts[1]]});
    }
    property bool panelShot: shot < 5 || shot >= 10
    property int barCount: shot === 6 ? 3 : shot >= 7 ? 120 : 0
    property var barFixture: ({count: barCount, accounts: [{status: shot === 8 ? "rate-limited" : shot === 9 ? "signed-out" : "ok"}]})
    TestEvent { id: input }
    QtObject {
        id: theme
        property color foreground: root.light ? "#253831" : "#e6f1e9"
        property color background: root.light ? "#f3f8f1" : "#10231c"
        property color accent: root.light ? "#32644c" : "#8bc9a6"
        property color success: root.light ? "#31714b" : "#88cc9b"
        property color failure: root.light ? "#a63143" : "#fa959c"
        property color running: root.light ? "#825b15" : "#f2c87e"
        property var palette: ({color0: String(background), color1: String(failure), color2: String(success),
            color3: String(running), color4: String(accent), color7: String(foreground)})
        property string fontFamily: Bar.DesktopFonts.family
        property int headingSize: 16
        property int bodySize: 13
        property int captionSize: 12
        property int barTextSize: 14
        property int radius: 6
        property bool observed: true
        property string detail: ""
        property var controls: ({button: button, dropdown: dropdown, toggle: toggle, textField: field, countBadge: badge})
    }
    Component { id: button; Bar.PanelButton { foreground: theme.foreground; text: "" } }
    Component { id: dropdown; Bar.ChoiceDropdown { foreground: theme.foreground; background: theme.background; gold: theme.accent } }
    Component { id: toggle; Bar.PanelSwitch { foreground: theme.foreground; accent: theme.accent } }
    Component { id: badge; Bar.CountBadge { accent: theme.accent } }
    Component { id: field; Bar.PanelTextField { foreground: theme.foreground; accent: theme.accent } }
    FloatingWindow {
        visible: true; implicitWidth: 660; implicitHeight: 700; color: theme.background
        Rectangle {
            id: canvas
            width: 620; height: panel.implicitHeight
            color: theme.background
            Plugin.GitHubPanel {
                id: panel
                anchors.fill: parent
                api: theme
                fixture: root.shot === 13 ? root.manyRepos : root.sample
                now: 1795445220000
                visible: root.panelShot
            }
            Rectangle {
                id: bar
                width: icon.implicitWidth + 12; height: 32
                color: theme.background
                visible: !root.panelShot
                Plugin.GitHubBarIcon {
                    id: icon
                    anchors.centerIn: parent
                    width: implicitWidth; height: implicitHeight
                    api: theme; fixture: root.barFixture
                }
            }
        }
    }
    function findItem(parent, name) {
        for (const child of parent.children) {
            if (child.objectName === name) return child;
            const match = findItem(child, name);
            if (match) return match;
        }
        return null;
    }
    Timer {
        interval: 240; running: true; repeat: true
        onTriggered: {
            if (root.step === 28) {
                const list = root.findItem(panel, "radarList");
                if (panel.selected !== "work" || list.contentHeight <= list.height || panel.implicitHeight !== 650)
                    throw new Error("Long queue must scroll inside the height cap");
                list.contentY = list.contentHeight - list.height;
                if (list.contentY <= 0) throw new Error("Long queue cannot reach its end");
                console.log("GITHUB_RENDER_OK");
                Qt.quit();
                return;
            }
            if (root.shot === 0) {
                if (panel.groups.map(group => group.length).join() !== "2,2,0,1"
                    || panel.groups[0][0].pr.number !== 18 || panel.implicitHeight > 650
                    || panel.collapsedSections.join() !== "fyi,waiting")
                    throw new Error("Fixture groups, sorting or layout missing");
            }
            if (root.shot < 2 && root.findItem(panel, "radarRow").highlighted)
                throw new Error("Default rows must not be highlighted");
            const dropdown = root.findItem(panel, "radarAccountDropdown").item;
            if (root.shot === 10) {
                if (panel.repositories.map(repo => repo.label + ":" + repo.count).join() !== "finch/atlas:2,lark/atlas:1,brush:1"
                    || panel.selectedRepo !== "" || !root.findItem(panel, "radarRepositoryHeading").visible)
                    throw new Error("All tab, repository order, collision labels or counts are wrong");
                if (dropdown.choices.map(choice => choice.label).join() !== "Personal · @snow-tern  4,Work · @violet-heron  8")
                    throw new Error("Account labels or counts are wrong");
            }
            if (root.shot === 11 && (panel.selectedRepo !== "lark/atlas" || panel.groups[0].length
                || panel.groups[1].length !== 1 || root.findItem(panel, "radarRepositoryHeading").visible))
                throw new Error("Repository tab did not filter rows and headings");
            if (root.shot === 12 && !dropdown.popup.opened)
                throw new Error("Shared account popup did not open");
            if (root.shot === 13) {
                const repositories = root.findItem(panel, "radarRepositoryDropdown").item;
                if (repositories.choices[0].value !== "" || repositories.choices.length !== panel.repositories.length + 1
                    || panel.repositories[3].label !== "almanac")
                    throw new Error("Repository dropdown must list All, then repositories sorted with ties by name");
            }
            if (root.shot === 1 && (panel.selected !== "work" || panel.groups[0].length !== 3))
                throw new Error("Work account filter missing");
            if (root.shot === 2) {
                const row = root.findItem(panel, "radarRow");
                input.mouseMove(row, row.width - 35, row.height / 2, 10, Qt.NoButton, Qt.NoModifier);
                if (!row.highlighted || root.findItem(row, "rowActions") || row.menuRequested !== undefined
                    || row.act !== undefined || !root.findItem(row, "ciStatus").visible)
                    throw new Error("Hovered row must keep CI visible and have no action controls");
                input.mouseClick(row, 54, row.height / 2, Qt.LeftButton, Qt.NoModifier, 10);
            }
            if (root.shot === 3) {
                const row = root.findItem(panel, "radarRow");
                input.mouseClick(row, 54, row.height / 2, Qt.RightButton, Qt.NoModifier, 10);
                if (panel.menuRow !== undefined) throw new Error("Row menu must be absent");
            }
            if (root.shot === 4 && !panel.showingSettings)
                throw new Error("Settings viewport missing");
            if (!root.panelShot && (icon.visibleCount !== (root.shot >= 8 ? 0 : root.barCount)
                || icon.muted !== (root.shot >= 8) || icon.implicitWidth !== 24 || !icon.countBadge))
                throw new Error("Bar badge state or slot changed");

            const names = ["personal", "work", "hover", "right-click", "settings", "bar-0", "bar-3", "bar-120", "bar-rate-limited", "bar-signed-out"];
            const roundFour = ["all", "repo", "account-dropdown", "many-repos"];
            const roundFive = root.shot === 4 || root.shot === 10 || root.shot === 11;
            const name = (roundFive ? "round5-" : "") + (root.shot >= 10 ? roundFour[root.shot - 10] : names[root.shot])
                + "-" + (root.light ? "light" : "dark");
            const target = root.panelShot ? canvas : bar;
            target.grabToImage(function(result) {
                if (!result.saveToFile((roundFive ? OUTPUT : TEMPORARY) + "/" + name + ".png")) throw new Error("Capture failed");
                root.step++;
                if (root.shot === 0) panel.forceActiveFocus();
                input.mouseMove(canvas, 1, 1, 10, Qt.NoButton, Qt.NoModifier);
                if (root.shot === 1 || root.shot === 2) {
                    dropdown.expanded = true;
                    dropdown.commit(root.shot === 1 ? 1 : 0);
                }
                if (root.shot === 4) {
                    const settings = root.findItem(panel, "radarSettingsButton");
                    input.mouseClick(settings, settings.width / 2, settings.height / 2, Qt.LeftButton, Qt.NoModifier, 10);
                    input.mouseMove(canvas, 1, 1, 10, Qt.NoButton, Qt.NoModifier);
                }
                if (root.shot === 5) panel.showingSettings = false;
                if (root.shot === 11) {
                    const repositories = root.findItem(panel, "radarRepositoryDropdown").item;
                    repositories.commit(repositories.choices.findIndex(choice => choice.value === "lark/atlas"));
                }
                if (root.shot === 12) {
                    canvas.Controls.Overlay.overlay.parent = canvas;
                    dropdown.expanded = true;
                }
                if (root.shot === 13) {
                    dropdown.commit(1);
                    if (panel.selected !== "work" || panel.selectedRepo !== "")
                        throw new Error("Repository choice leaked into another account");
                    dropdown.commit(0);
                    if (panel.selectedRepo !== "lark/atlas")
                        throw new Error("Switching accounts lost the repository choice");
                    const account = root.sample.accounts[0];
                    const withoutRepo = Object.assign({}, account, {rows: account.rows.filter(pr => pr.repo !== "lark/atlas")});
                    const previous = root.sample;
                    root.sample = Object.assign({}, previous, {accounts: [withoutRepo, previous.accounts[1]]});
                    if (panel.selectedRepo !== "") throw new Error("Missing repository must fall back to All");
                    panel.pendingRepositories = ({});
                    root.sample = previous;
                    panel.forceActiveFocus();
                }
                if (root.shot === 0) { panel.pendingAccount = ""; panel.pendingRepositories = ({}); }
                if (root.step === 28) {
                    const account = root.sample.accounts[1];
                    const personal = root.sample.accounts[0];
                    root.sample = Object.assign({}, root.sample, {accounts: [Object.assign({}, personal, {count: 0}), account]});
                    if (panel.selected !== "work")
                        throw new Error("First account with actionable items must take precedence");
                    const extra = Array.from({length: 30}, (unused, index) => Object.assign({}, account.rows[0], {
                        id: "extra-" + index, number: 100 + index
                    }));
                    const expanded = Object.assign({}, account, {rows: account.rows.concat(extra)});
                    root.sample = Object.assign({}, root.sample, {accounts: [personal, expanded], selected_account: "work"});
                }
            });
        }
    }
}
'''


@unittest.skipUnless(shutil.which("quickshell"), "Quickshell required for offscreen rendering")
class GitHubRenderTests(unittest.TestCase):
    def test_bar_observes_creation_and_atomic_replacement_of_snapshot(self):
        fixture = '''import QtQuick
import Quickshell
import Quickshell.Io
import "github" as Plugin

ShellRoot {
    id: root
    property int step: 0
    QtObject {
        id: theme
        property color foreground: "white"
        property string fontFamily: "Sans"
        property string detail: ""
        property int barTextSize: 14
    }
    FloatingWindow {
        visible: true; implicitWidth: 120; implicitHeight: 100
        Plugin.GitHubBarIcon { id: icon; api: theme }
    }
    Process {
        id: writer
        command: ["python3", "WRITER", String(root.step === 0 ? 3 : 5)]
    }
    Timer {
        interval: 100; running: true; repeat: true
        onTriggered: {
            if (root.step === 0 && !writer.running) {
                writer.running = true;
                root.step = 1;
            } else if (root.step === 1 && icon.count === 3 && icon.implicitWidth > 24 && !writer.running) {
                writer.running = true;
                root.step = 2;
            } else if (root.step === 2 && icon.count === 5) {
                console.log("GITHUB_WATCH_OK"); Qt.quit();
            }
        }
    }
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            shutil.copytree(ROOT / "plugins/github", folder / "github")
            target = folder / "eitr/plugins/github/snapshot.json"
            target.parent.mkdir(parents=True)
            writer = folder / "writer.py"
            writer.write_text(f"""import json
import sys
from pathlib import Path
path = Path({str(target)!r})
temporary = path.with_suffix(".tmp")
temporary.write_text(json.dumps({{"accounts": [{{"status": "ok"}}], "count": int(sys.argv[1])}}))
temporary.replace(path)
""")
            path = folder / "GitHubWatch.qml"
            path.write_text(fixture.replace("WRITER", str(writer)))
            status, log = rendering.render(path, rendering.render_environment(folder), 6)
        self.assertEqual(status, 0, log)
        self.assertIn("GITHUB_WATCH_OK", log)

    def test_account_panel_and_bar_badges_in_both_themes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            output = Path(os.environ.get("EITR_GITHUB_RENDERS", temporary))
            output.mkdir(parents=True, exist_ok=True)
            rendering.copy_runtime(folder / "runtime")
            shutil.copytree(ROOT / "plugins/github", folder / "github")
            fixture = FIXTURE.replace("SNAPSHOT", json.dumps(snapshot())).replace("OUTPUT", json.dumps(str(output))).replace("TEMPORARY", json.dumps(temporary))
            path = folder / "GitHubRender.qml"
            path.write_text(fixture)
            environment = rendering.render_environment(folder)
            state = Path(environment["XDG_STATE_HOME"]) / "eitr/plugins/github"
            state.mkdir(parents=True, exist_ok=True)
            (state / "snapshot.json").write_text(json.dumps(snapshot()))
            browser_log = folder / "browser.log"
            opener = folder / "xdg-open"
            opener.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$GITHUB_BROWSER_LOG"\n')
            opener.chmod(0o755)
            environment["PATH"] = str(folder) + os.pathsep + os.environ["PATH"]
            environment["GITHUB_BROWSER_LOG"] = str(browser_log)
            status, log = rendering.render(path, environment, 12)
            for theme in ("dark", "light"):
                for kind in ("all", "repo", "settings"):
                    capture = output / f"round5-{kind}-{theme}.png"
                    self.assertTrue(capture.is_file(), log)
                    self.assertGreater(capture.stat().st_size, 200)
            self.assertTrue(browser_log.is_file(), log)
            self.assertEqual(browser_log.read_text().splitlines(), [snapshot()["accounts"][0]["rows"][0]["url"]] * 2)
        self.assertEqual(status, 0, log)
        self.assertIn("GITHUB_RENDER_OK", log)
        for warning in ("QML error", "ReferenceError", "TypeError", "Binding loop", "Could not create"):
            self.assertNotIn(warning, log)
