import QtQuick
import Eitr as Eitr
import "TailscaleState.js" as TailscaleState

// One device, in Eitr's 36 px selectable-row metrics: glyph in the 10 px leading
// slot, name and detail from 36 px with a 2 px gap, 24×24 actions inset 4 px.
// Hovering an action names it in the detail line instead of a tooltip.
Rectangle {
    id: row
    required property var api
    required property var peer
    property bool canSend: false
    property bool copied: false
    signal sendRequested(string address)
    signal copyRequested(string address)

    implicitHeight: 36
    radius: api.radius
    color: Qt.alpha(api.foreground, rowHover.hovered ? 0.1 : 0.04)
    border.width: 1
    border.color: Qt.alpha(api.foreground, 0.15)
    readonly property string connectionText: Eitr.I18n.tr(TailscaleState.connectionLabels[peer.connection] || "Offline")
    readonly property string detail: sendButton.hovered ? Eitr.I18n.tr("Send files with Taildrop")
        : copyButton.hovered ? Eitr.I18n.tr("Copy {address}", {address: peer.address})
        : copied ? Eitr.I18n.tr("Copied {address}", {address: peer.address})
        : (peer.address ? peer.address + " · " : "") + connectionText

    HoverHandler { id: rowHover }
    Text {
        x: 10
        width: 18
        anchors.verticalCenter: parent.verticalCenter
        horizontalAlignment: Text.AlignHCenter
        text: TailscaleState.isMobile(row.peer.os) ? "\u{F011C}" : "\u{F0379}"
        textFormat: Text.PlainText
        color: row.api.foreground
        opacity: row.peer.online ? 1 : 0.45
        font.family: row.api.fontFamily
        font.pixelSize: 18
    }
    Column {
        x: 36
        width: actions.x - x - 6
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2
        Text {
            width: parent.width
            text: row.peer.name
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: row.api.foreground
            opacity: row.peer.online ? 1 : 0.72
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
        TailscaleButton {
            id: sendButton
            api: row.api
            visible: row.canSend
            glyph: "\u{F0552}"
            description: Eitr.I18n.tr("Send files with Taildrop")
            onClicked: row.sendRequested(row.peer.address)
        }
        TailscaleButton {
            id: copyButton
            api: row.api
            visible: row.peer.address !== ""
            glyph: "\u{F018F}"
            description: Eitr.I18n.tr("Copy address")
            onClicked: row.copyRequested(row.peer.address)
        }
    }
}
