import QtQuick
import "Strings.js" as Strings

Item {
    id: root
    required property var api
    property var fixture: null
    readonly property int count: snapshot.value.count
    readonly property bool muted: !snapshot.value.accounts.some(account => account.status === "ok")
        || snapshot.value.accounts.some(account => account.status === "rate-limited")
    readonly property string detail: count > 0 ? Strings.tr(count === 1 ? "1 pull request needs you" : "%1 pull requests need you").replace("%1", count)
        : snapshot.value.accounts.some(account => account.status === "signed-out")
          ? Strings.tr("Log in through Git Accounts") : ""

    readonly property var countBadge: api.controls && api.controls.countBadge
    readonly property int visibleCount: muted ? 0 : count

    implicitWidth: contents.implicitWidth
    implicitHeight: 24
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    Accessible.name: "GitHub"
    Accessible.description: root.detail
    onDetailChanged: api.detail = detail
    Component.onCompleted: api.detail = detail

    RadarSnapshot { id: snapshot; observing: root.api.observed !== false; fixture: root.fixture }
    Row {
        id: contents
        anchors.centerIn: parent
        // Natural-size side slots rotate their content. Keep the square icon and badge upright.
        rotation: root.countBadge && root.api.verticalBar && !root.api.compactBarItem ? -90 : 0
        spacing: 3

        RadarText {
            api: root.api
            anchors.verticalCenter: parent.verticalCenter
            width: 24
            horizontalAlignment: Text.AlignHCenter
            text: "\u{F09B}"
            font.pixelSize: 16
            font.family: "JetBrainsMono Nerd Font"
            opacity: root.muted ? 0.45 : 1

            Loader {
                anchors.fill: parent
                sourceComponent: root.countBadge || null
                onLoaded: item.count = Qt.binding(() => root.visibleCount)
            }
        }
        RadarText {
            api: root.api
            anchors.verticalCenter: parent.verticalCenter
            visible: !root.countBadge && root.visibleCount > 0
            text: String(root.visibleCount)
            color: root.api.accent || root.api.foreground
            font.bold: true
            font.pixelSize: root.api.barTextSize
        }
    }
}
