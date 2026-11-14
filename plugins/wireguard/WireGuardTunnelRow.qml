import QtQuick
import Eitr as Eitr

// One imported WireGuard tunnel in Eitr's 36 px row metrics: glyph in the 10 px leading
// slot, name and detail from 36 px with a 2 px gap, remove button and connect switch on the right.
Rectangle {
    id: row
    required property var api
    required property var tunnel
    property bool switchEnabled: true
    signal toggleRequested(string target, bool connect)
    signal removeRequested(string target, string name)

    implicitHeight: 36
    radius: api.radius
    color: Qt.alpha(api.foreground, rowHover.hovered ? 0.1 : row.tunnel.connected ? 0.08 : 0.04)
    border.width: row.tunnel.connected ? 0 : 1
    border.color: Qt.alpha(api.foreground, 0.15)
    readonly property string stateText: row.tunnel.connected ? Eitr.I18n.tr("Connected")
        : row.tunnel.state === "connecting" ? Eitr.I18n.tr("Connecting…") : Eitr.I18n.tr("Disconnected")
    readonly property string detail: removeButton.hovered ? Eitr.I18n.tr("Remove {name}", {name: row.tunnel.name})
        : (row.tunnel.endpoint ? row.tunnel.endpoint + " · " : "") + stateText

    HoverHandler { id: rowHover }
    Text {
        x: 10
        width: 18
        anchors.verticalCenter: parent.verticalCenter
        horizontalAlignment: Text.AlignHCenter
        text: row.tunnel.connected ? "\u{F033E}" : "\u{F0341}"
        textFormat: Text.PlainText
        color: row.api.foreground
        opacity: row.tunnel.connected ? 1 : 0.45
        font.family: row.api.fontFamily
        font.pixelSize: 17
    }
    Column {
        x: 36
        width: Math.max(0, actions.x - x - 6)
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            width: parent.width
            text: row.tunnel.name
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: row.api.foreground
            opacity: row.tunnel.connected ? 1 : 0.72
            font.family: row.api.fontFamily
            font.pixelSize: row.api.bodySize
        }
        Text {
            width: parent.width
            text: row.detail
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: row.api.foreground
            opacity: 0.72
            font.family: row.api.fontFamily
            font.pixelSize: row.api.captionSize
            font.features: {"tnum": 1}
        }
    }
    Row {
        id: actions
        x: row.width - width - 4
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6
        WireGuardButton {
            id: removeButton
            api: row.api
            anchors.verticalCenter: parent.verticalCenter
            glyph: "\u{F01B4}"
            description: Eitr.I18n.tr("Remove {name}", {name: row.tunnel.name})
            onClicked: row.removeRequested(row.tunnel.id, row.tunnel.name)
        }
        WireGuardSwitch {
            api: row.api
            anchors.verticalCenter: parent.verticalCenter
            enabled: row.switchEnabled
            checked: row.tunnel.connected === true
            description: row.tunnel.name
            onToggled: row.toggleRequested(row.tunnel.id, !row.tunnel.connected)
        }
    }
}
