import QtQuick
import "Strings.js" as Strings
import "PhoneState.js" as State

Column {
    id: row
    required property var api
    required property var device
    property bool busy: false
    property bool expanded: false
    property bool confirming: false
    readonly property bool connected: device.paired && device.reachable
    signal actionRequested(string action, string identifier, var payload)
    width: parent.width
    spacing: 6

    function supports(plugin) { return connected && device.plugins.indexOf("kdeconnect_" + plugin) !== -1; }
    function act(action, payload) { actionRequested(action, device.id, payload || ({})); }

    Rectangle {
        width: parent.width
        height: 36
        radius: row.api.radius
        color: Qt.alpha(row.api.foreground, row.expanded ? 0.18 : 0.04)
        border.width: row.expanded ? 0 : 1
        border.color: Qt.alpha(row.api.foreground, 0.15)
        Text {
            x: 10; anchors.verticalCenter: parent.verticalCenter
            text: State.glyph(row.device.type)
            color: row.api.foreground
            font.family: "JetBrainsMono Nerd Font"
            font.pixelSize: 18
            opacity: row.connected ? 1 : 0.55
        }
        Column {
            x: 36; width: parent.width - x - deviceButton.width - 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            PhoneLabel {
                api: row.api; width: parent.width
                text: row.device.name
                wrapMode: Text.NoWrap; elide: Text.ElideRight
            }
            PhoneLabel {
                api: row.api; width: parent.width
                font.pixelSize: 11; opacity: 0.72
                wrapMode: Text.NoWrap; elide: Text.ElideRight
                text: row.device.incoming ? Strings.tr("Pairing request")
                    : row.connected ? (row.device.battery === null ? Strings.tr("Connected")
                        : row.device.battery + "% · " + Strings.tr(row.device.charging ? "Charging" : "On battery"))
                    : row.device.paired ? Strings.tr("Offline")
                    : row.device.outgoing ? Strings.tr("Waiting for phone") : Strings.tr("Available")
            }
        }
        PhoneButton {
            id: deviceButton
            api: row.api
            anchors.right: parent.right; anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            height: 28
            text: !row.device.paired && !row.device.incoming ? Strings.tr("Pair")
                : row.expanded ? Strings.tr("Hide actions") : Strings.tr("Actions")
            available: row.device.paired || row.device.incoming || (!row.busy && row.device.reachable && !row.device.outgoing)
            selected: row.expanded
            onClicked: {
                if (!row.device.paired && !row.device.incoming) { row.act("pair"); return; }
                row.expanded = !row.expanded; row.confirming = false;
            }
        }
    }
    Column {
        width: parent.width
        visible: row.device.incoming || row.expanded
        spacing: 6
        PhoneLabel {
            api: row.api; width: parent.width
            visible: row.device.incoming
            font.pixelSize: 12; opacity: 0.72
            text: Strings.tr("Accept only if this is your phone. Compare the pairing code on both devices.")
        }
        PhoneLabel {
            api: row.api; width: parent.width
            visible: (row.device.incoming || row.device.outgoing) && !!row.device.verification
            text: row.device.verification || ""
            font.pixelSize: 11
            wrapMode: Text.WrapAnywhere
        }
        Flow {
            width: parent.width; spacing: 6
            PhoneButton {
                api: row.api; visible: row.device.incoming
                text: Strings.tr("Accept"); available: !row.busy
                onClicked: row.act("accept")
            }
            PhoneButton {
                api: row.api; visible: row.device.incoming
                text: Strings.tr("Reject"); available: !row.busy
                onClicked: row.act("reject")
            }
            PhoneButton {
                api: row.api; visible: !row.device.paired && !row.device.incoming
                text: Strings.tr("Pair"); available: !row.busy && row.device.reachable && !row.device.outgoing
                onClicked: row.act("pair")
            }
            PhoneButton {
                api: row.api; visible: row.device.paired
                text: Strings.tr("Unpair"); available: !row.busy
                onClicked: row.confirming = true
            }
            PhoneButton {
                api: row.api; visible: row.connected
                text: Strings.tr("Send files"); available: !row.busy && row.supports("share")
                onClicked: row.act("send")
            }
            PhoneButton {
                api: row.api; visible: row.connected
                text: Strings.tr("Send clipboard"); available: !row.busy && row.supports("share")
                onClicked: row.act("clipboard")
            }
            PhoneButton {
                api: row.api; visible: row.connected
                text: Strings.tr("Ring my phone"); available: !row.busy && row.supports("findmyphone")
                onClicked: row.act("ring")
            }
            PhoneButton {
                api: row.api; visible: row.connected
                text: Strings.tr("Ping"); available: !row.busy && row.supports("ping")
                onClicked: row.act("ping")
            }
            PhoneButton {
                api: row.api; visible: row.connected
                text: Strings.tr("Browse files"); available: !row.busy && row.supports("sftp")
                onClicked: row.act("browse")
            }
        }
        PhoneLabel {
            api: row.api; width: parent.width
            visible: row.connected
            text: Strings.tr("Disabled actions are not shared by this phone.")
            font.pixelSize: 11; opacity: 0.72
        }
        Column {
            width: parent.width; spacing: 6
            visible: row.confirming
            PhoneLabel {
                api: row.api; width: parent.width
                text: Strings.tr("Unpair this device? You will need to pair it again to reconnect.")
            }
            Flow {
                width: parent.width; spacing: 6
                PhoneButton {
                    api: row.api; text: Strings.tr("Confirm unpair"); available: !row.busy
                    onClicked: { row.act("unpair", {confirmed: true}); row.confirming = false; }
                }
                PhoneButton {
                    api: row.api; text: Strings.tr("Cancel")
                    onClicked: row.confirming = false
                }
            }
        }
    }
}
