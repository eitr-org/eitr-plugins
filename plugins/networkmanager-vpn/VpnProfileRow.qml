import QtQuick
import Eitr as Eitr

// One NetworkManager VPN profile (OpenVPN, OpenConnect or WireGuard) in Eitr's 36 px
// row metrics: glyph in the 10 px leading slot, name and protocol/state detail from
// 36 px with a 2 px gap, and a connect/disconnect switch on the right.
Rectangle {
    id: row
    required property var api
    required property var profile
    property bool switchEnabled: true
    signal toggleRequested(string identifier, bool connect)

    implicitHeight: 36
    radius: api.radius
    color: Qt.alpha(api.foreground, rowHover.hovered ? 0.1 : row.profile.connected ? 0.08 : 0.04)
    border.width: row.profile.connected ? 0 : 1
    border.color: Qt.alpha(api.foreground, 0.15)
    readonly property string stateText: row.profile.connected ? Eitr.I18n.tr("Connected")
        : row.profile.state === "connecting" ? Eitr.I18n.tr("Connecting…") : Eitr.I18n.tr("Disconnected")
    readonly property string detail: (row.profile.typeLabel ? row.profile.typeLabel + " · " : "")
        + (row.profile.connected && row.profile.address ? row.profile.address + " · " : "") + stateText

    HoverHandler { id: rowHover }
    Text {
        x: 10
        width: 18
        anchors.verticalCenter: parent.verticalCenter
        horizontalAlignment: Text.AlignHCenter
        text: row.profile.connected ? "\u{F0483}" : "\u{F033E}"
        textFormat: Text.PlainText
        color: row.api.foreground
        opacity: row.profile.connected ? 1 : 0.45
        font.family: row.api.fontFamily
        font.pixelSize: 17
    }
    Column {
        x: 36
        width: Math.max(0, profileSwitch.x - x - 6)
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            width: parent.width
            text: row.profile.name
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: row.api.foreground
            opacity: row.profile.connected ? 1 : 0.72
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
    VpnSwitch {
        id: profileSwitch
        x: row.width - width - 4
        anchors.verticalCenter: parent.verticalCenter
        api: row.api
        enabled: row.switchEnabled
        checked: row.profile.connected === true
        description: row.profile.name
        onToggled: row.toggleRequested(row.profile.id, !row.profile.connected)
    }
}
