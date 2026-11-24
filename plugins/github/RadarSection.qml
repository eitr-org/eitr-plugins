import QtQuick
import QtQuick.Layouts
import "RadarPresentation.js" as Presentation

ColumnLayout {
    id: section
    required property var api
    required property string heading
    required property var rows
    required property bool expanded
    required property bool actionable
    required property real now
    required property bool showRepositories
    signal toggle()
    signal openRequested(string account, string pr)
    visible: rows.length > 0
    spacing: 6

    Item {
        Layout.fillWidth: true
        implicitHeight: 28
        activeFocusOnTab: section.visible
        Accessible.role: Accessible.Button
        Accessible.name: section.heading + " · " + section.rows.length
        Accessible.expanded: section.expanded
        Accessible.onPressAction: section.toggle()
        Keys.onSpacePressed: section.toggle()
        Keys.onReturnPressed: section.toggle()
        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: section.toggle() }

        Rectangle {
            anchors.fill: parent
            radius: Math.min(section.api.radius, 4)
            color: Qt.alpha(section.api.foreground, hover.hovered || parent.activeFocus ? 0.1 : 0)
        }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 6
            anchors.rightMargin: 6
            spacing: 8
            RadarText {
                api: section.api
                text: section.expanded ? "\u{F078}" : "\u{F054}"
                font.pixelSize: 11
                font.family: "JetBrainsMono Nerd Font"
                opacity: 0.72
            }
            RadarText {
                api: section.api
                text: section.heading
                font.bold: true
                color: section.actionable ? Presentation.tone(api, "accent") : api.foreground
                Layout.fillWidth: true
                elide: Text.ElideRight
            }
            RadarChip { api: section.api; label: String(section.rows.length) }
        }
    }

    // Rows keep their order; consecutive groups follow each repository's first row.
    readonly property var repositories: {
        const groups = [];
        const index = {};
        for (const entry of rows) {
            const key = entry.account.id + "/" + entry.pr.repo;
            if (!(key in index)) {
                index[key] = groups.length;
                groups.push({repo: entry.pr.repo, rows: []});
            }
            groups[index[key]].rows.push(entry);
        }
        return groups;
    }

    Repeater {
        model: section.expanded ? section.repositories : []
        ColumnLayout {
            id: repository
            required property var modelData
            Layout.fillWidth: true
            spacing: 4
            RowLayout {
                objectName: "radarRepositoryHeading"
                visible: section.showRepositories
                Layout.fillWidth: true
                Layout.leftMargin: 6
                Layout.topMargin: 4
                spacing: 6
                opacity: 0.72
                RadarText {
                    api: section.api
                    text: "\u{F401}"
                    font.family: "JetBrainsMono Nerd Font"
                    font.pixelSize: api.captionSize
                }
                RadarText {
                    api: section.api
                    Layout.fillWidth: true
                    text: repository.modelData.repo
                    elide: Text.ElideMiddle
                    font.pixelSize: api.captionSize
                    font.bold: true
                }
            }
            Repeater {
                model: repository.modelData.rows
                RadarRow {
                    required property var modelData
                    objectName: "radarRow"
                    Layout.fillWidth: true
                    api: section.api
                    pr: modelData.pr
                    account: modelData.account
                    now: section.now
                    showRepo: false
                    onOpenRequested: section.openRequested(account.id, pr.id)
                }
            }
        }
    }
}
