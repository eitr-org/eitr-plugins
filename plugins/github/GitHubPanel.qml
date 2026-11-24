import QtQuick
import QtQuick.Controls.Basic as Controls
import QtQuick.Layouts
import Quickshell
import "RadarActions.js" as Actions
import "RadarPresentation.js" as Presentation
import "Strings.js" as Strings

Item {
    id: panel
    required property var api
    property var fixture: null
    property bool showingSettings: false
    property string pendingAccount: ""
    property real now: Date.now()
    property var pendingSections: null
    property var pendingRepositories: ({})
    readonly property var accounts: snapshot.value.accounts
    readonly property string savedAccount: snapshot.value.selected_account || ""
    readonly property var selectedAccount: accounts.find(account => account.id === (pendingAccount || savedAccount))
        || accounts.find(account => account.count > 0) || accounts[0]
    readonly property string selected: selectedAccount ? selectedAccount.id : ""
    readonly property var repositories: Presentation.repositories(selectedAccount ? selectedAccount.rows : [])
    readonly property var savedRepositories: snapshot.value.selected_repositories || ({})
    readonly property string selectedRepo: {
        const wanted = pendingRepositories[selected] ?? savedRepositories[selected];
        return repositories.some(repo => repo.name === wanted) ? wanted : "";
    }
    readonly property var groups: buildGroups()
    readonly property var sectionKeys: ["own", "others", "fyi", "waiting"]
    readonly property var groupNames: ["Your PRs: your move", "Others’ PRs: your move", "FYI", "Waiting"]
    readonly property var savedSections: snapshot.value.options.collapsed_sections || ["fyi", "waiting"]
    readonly property var collapsedSections: pendingSections || savedSections
    readonly property bool refreshing: !!snapshot.value.refreshing || refreshTimeout.running

    // Leave room for the dropdown in the host window even when the queue is empty.
    readonly property int accountPopupHeight: accountDropdown.visible ? 92 + 42 * Math.min(accounts.length, 3) : 0
    implicitHeight: Math.min(650, Math.max(body.implicitHeight + 36, accountPopupHeight))

    function execute(args) {
        Quickshell.execDetached(["env", "PYTHONDONTWRITEBYTECODE=1", decodeURIComponent(Qt.resolvedUrl("action.py").toString())
            .replace(/^file:\/\//, "")].concat(args));
    }
    function send(payload) {
        execute(Actions.message(payload));
    }
    function refresh() {
        if (refreshing) return;
        refreshTimeout.restart();
        send({operation: "refresh"});
    }
    function selectAccount(identifier) {
        if (identifier === selected) return;
        pendingAccount = identifier;
        if (!fixture) {
            accountSaveTimeout.restart();
            send({operation: "select-account", account: identifier});
        }
    }
    function selectRepository(repository) {
        if (repository === selectedRepo) return;
        pendingRepositories = Object.assign({}, pendingRepositories, {[selected]: repository});
        if (!fixture) {
            repositorySaveTimeout.restart();
            send({operation: "select-repository", account: selected, repository: repository});
        }
    }
    function toggleSection(key) {
        pendingSections = collapsedSections.includes(key)
            ? collapsedSections.filter(section => section !== key) : collapsedSections.concat(key);
        saveTimeout.restart();
        send({operation: "setting", key: "collapsed_sections", value: pendingSections});
    }
    function buildGroups() {
        const result = [[], [], [], []];
        if (selectedAccount) {
            for (const pr of selectedAccount.rows) {
                if (!selectedRepo || pr.repo === selectedRepo)
                    result[pr.group].push({account: selectedAccount, pr: pr});
            }
        }
        for (const group of result.slice(0, 2))
            group.sort((left, right) => (left.pr.waiting_since || left.pr.updated).localeCompare(right.pr.waiting_since || right.pr.updated));
        for (const group of result.slice(2))
            group.sort((left, right) => right.pr.updated.localeCompare(left.pr.updated));
        return result;
    }
    function statusText(account) {
        switch (account.status) {
        case "signed-out": return Strings.tr("Log in through Git Accounts");
        case "rate-limited": return Strings.tr("Rate limit resets") + " " + Actions.resetTime(account.reset);
        default: return "";
        }
    }

    onSavedAccountChanged: {
        if (savedAccount === pendingAccount) {
            accountSaveTimeout.stop();
            pendingAccount = "";
        }
    }
    function acknowledgeRepositories() {
        const confirmed = Object.keys(pendingRepositories).filter(account =>
            (savedRepositories[account] || "") === pendingRepositories[account]);
        if (!confirmed.length) return;
        const remaining = Object.assign({}, pendingRepositories);
        for (const account of confirmed)
            delete remaining[account];
        pendingRepositories = remaining;
    }
    onSavedRepositoriesChanged: Qt.callLater(acknowledgeRepositories)
    onSavedSectionsChanged: {
        if (pendingSections && JSON.stringify(pendingSections) === JSON.stringify(savedSections))
            pendingSections = null;
    }
    onShowingSettingsChanged: {
        if (showingSettings) settingsView.contentY = 0;
    }
    function resetQueue() {
        listView.contentY = 0;
    }
    onSelectedChanged: Qt.callLater(resetQueue)
    onSelectedRepoChanged: Qt.callLater(resetQueue)

    RadarSnapshot {
        id: snapshot
        observing: panel.api.observed !== false
        fixture: panel.fixture
        onValueChanged: if (!value.refreshing) refreshTimeout.stop()
    }
    Timer { id: refreshTimeout; interval: 15000 }
    Timer { id: accountSaveTimeout; interval: 15000; onTriggered: panel.pendingAccount = "" }
    Timer { id: repositorySaveTimeout; interval: 15000; onTriggered: panel.pendingRepositories = ({}) }
    Timer { id: saveTimeout; interval: 15000; onTriggered: panel.pendingSections = null }
    Timer {
        interval: 15000; repeat: true; triggeredOnStart: true
        running: panel.visible && panel.api.observed !== false && !panel.fixture
        onTriggered: panel.now = Date.now()
    }
    Shortcut {
        sequence: "Ctrl+R"
        enabled: panel.visible && panel.api.observed !== false
        onActivated: panel.refresh()
    }
    Shortcut {
        sequence: "Escape"
        enabled: panel.visible && panel.showingSettings
        onActivated: panel.showingSettings = false
    }

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            RadarButton {
                api: panel.api
                glyph: "\u{F053}"
                label: Strings.tr("Back")
                visible: panel.showingSettings
                onClicked: panel.showingSettings = false
            }
            RadarText {
                api: panel.api
                Layout.fillWidth: true
                text: panel.showingSettings ? Strings.tr("Settings") : "GitHub"
                font.pixelSize: api.headingSize
                font.bold: true
            }
            RadarButton {
                api: panel.api
                visible: !panel.showingSettings
                glyph: "\u{F021}"
                label: Strings.tr("Refresh")
                spinning: panel.refreshing
                onClicked: panel.refresh()
            }
            RadarButton {
                api: panel.api
                visible: !panel.showingSettings
                objectName: "radarSettingsButton"
                glyph: "\u{F013}"
                label: Strings.tr("Settings")
                onClicked: panel.showingSettings = true
            }
        }

        // Account first, then its repositories: All, then each repository with open pull requests.
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            visible: !panel.showingSettings && panel.accounts.length > 0
            Loader {
                id: accountDropdown
                objectName: "radarAccountDropdown"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                sourceComponent: panel.api.controls.dropdown
                onLoaded: {
                    item.floatingLabel = Strings.tr("Account");
                    item.helperText = "";
                    item.choices = Qt.binding(() => panel.accounts.map(account => ({
                        value: account.id,
                        label: account.label + (account.login ? " · @" + account.login : "") + "  " + account.count
                    })));
                    item.current = Qt.binding(() => panel.selected);
                    item.chosen.connect(panel.selectAccount);
                }
            }
            Loader {
                id: repositoryDropdown
                objectName: "radarRepositoryDropdown"
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                sourceComponent: panel.api.controls.dropdown
                onLoaded: {
                    item.floatingLabel = Strings.tr("Repository");
                    item.helperText = "";
                    item.choices = Qt.binding(() => [{value: "", label: Strings.tr("All") + "  " + (panel.selectedAccount ? panel.selectedAccount.count : 0)}]
                        .concat(panel.repositories.map(repository => ({value: repository.name, label: repository.label + "  " + repository.count}))));
                    item.current = Qt.binding(() => panel.selectedRepo);
                    item.chosen.connect(panel.selectRepository);
                }
            }
        }

        RadarText {
            api: panel.api
            Layout.fillWidth: true
            id: statusLine
            visible: !panel.showingSettings && text !== ""
            text: panel.selectedAccount ? panel.statusText(panel.selectedAccount)
                : Strings.tr("Log in through Git Accounts")
            elide: Text.ElideRight
            opacity: 0.72
            HoverHandler { id: statusHover }
            RadarTooltip {
                api: panel.api
                visible: statusHover.hovered && statusLine.truncated
                text: statusLine.text
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            implicitHeight: panel.showingSettings ? settingsView.contentHeight : listView.contentHeight

            Flickable {
                id: listView
                objectName: "radarList"
                anchors.fill: parent
                visible: !panel.showingSettings
                clip: true
                contentWidth: width
                contentHeight: sections.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                Controls.ScrollBar.vertical: Controls.ScrollBar { }
                ColumnLayout {
                    id: sections
                    width: parent.width - (listView.contentHeight > listView.height ? 10 : 0)
                    spacing: 6
                    Repeater {
                        model: panel.groupNames.length
                        RadarSection {
                            required property int index
                            Layout.fillWidth: true
                            api: panel.api
                            heading: Strings.tr(panel.groupNames[index])
                            rows: panel.groups[index]
                            showRepositories: panel.selectedRepo === ""
                            expanded: !panel.collapsedSections.includes(panel.sectionKeys[index])
                            actionable: index < 2
                            now: panel.now
                            onToggle: panel.toggleSection(panel.sectionKeys[index])
                            onOpenRequested: (account, pr) => panel.execute(["open", account, pr])
                        }
                    }
                }
            }
            Flickable {
                id: settingsView
                objectName: "radarSettings"
                anchors.fill: parent
                visible: panel.showingSettings
                clip: true
                contentWidth: width
                contentHeight: settingsLoader.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                Controls.ScrollBar.vertical: Controls.ScrollBar { }
                Loader {
                    id: settingsLoader
                    width: settingsView.width - 10
                    active: panel.showingSettings
                    sourceComponent: RadarSettings {
                        api: panel.api
                        accounts: panel.accounts
                        options: snapshot.value.options
                        onSave: (key, value, account) => panel.send({operation: "setting", key: key, value: value, account: account})
                    }
                }
            }
        }
    }
}
