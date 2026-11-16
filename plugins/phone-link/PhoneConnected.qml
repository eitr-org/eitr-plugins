import QtQuick
import "Strings.js" as Strings
import "PhoneState.js" as State

Column {
    id: card
    required property var api
    required property var device
    property bool busy: false
    signal actionRequested(string action, string identifier, var payload)
    width: parent.width
    spacing: 12

    function supports(plugin) { return device.plugins.indexOf("kdeconnect_" + plugin) !== -1; }

    Rectangle {
        objectName: "connected-header"
        width: parent.width; height: 64
        radius: card.api.radius
        color: Qt.alpha(card.api.foreground, 0.18)
        PhoneLabel {
            api: card.api; x: 14
            anchors.verticalCenter: parent.verticalCenter
            text: State.glyph(card.device.type)
            font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 24
        }
        Column {
            x: 50; width: parent.width - x - 14
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4
            PhoneLabel {
                api: card.api; width: parent.width
                text: card.device.name; font.pixelSize: card.api.bodySize; font.bold: true
                wrapMode: Text.NoWrap; elide: Text.ElideRight
            }
            Row {
                spacing: 8
                Rectangle {
                    visible: card.device.battery !== null
                    width: 46; height: 4; radius: Math.min(2, card.api.radius)
                    anchors.verticalCenter: parent.verticalCenter
                    color: Qt.alpha(card.api.foreground, 0.16)
                    Rectangle {
                        width: parent.width * Math.max(0, Math.min(100, card.device.battery || 0)) / 100
                        height: parent.height; radius: parent.radius; color: card.api.foreground
                    }
                }
                PhoneLabel {
                    objectName: "battery-caption"
                    api: card.api; font.pixelSize: card.api.captionSize; opacity: 0.72
                    text: card.device.battery === null ? Strings.tr("Connected")
                        : card.device.battery + "% · " + (card.device.charging
                            ? "󱐋 " + Strings.tr("Charging") : Strings.tr("On battery"))
                }
            }
        }
    }
    Grid {
        objectName: "action-grid"
        width: parent.width; columns: 3; spacing: 6
        readonly property real tileHeight: children.reduce((height, child) => Math.max(height, child.implicitHeight || 0), 58)
        Repeater {
            model: [
                {action: "send", label: "Send files", glyph: "󰈔", plugin: "share"},
                {action: "clipboard", label: "Send clipboard", glyph: "󰅌", plugin: "share"},
                {action: "ring", label: "Ring", glyph: "󰂚", plugin: "findmyphone"},
                {action: "ping", label: "Ping", glyph: "󰓅", plugin: "ping"},
                {action: "browse", label: "Browse files", glyph: "󰉋", plugin: "sftp"}
            ]
            PhoneActionTile {
                required property var modelData
                objectName: "action-" + modelData.action
                api: card.api; width: (parent.width - 12) / 3; height: parent.tileHeight
                text: Strings.tr(modelData.label); glyph: modelData.glyph
                supported: card.supports(modelData.plugin); busy: card.busy
                onClicked: card.actionRequested(modelData.action, card.device.id, {})
            }
        }
        Item { width: (parent.width - 12) / 3; height: parent.tileHeight }
    }
    PhoneUnpair {
        api: card.api; width: parent.width; busy: card.busy
        onConfirmed: card.actionRequested("unpair", card.device.id, {confirmed: true})
    }
}
