import QtQuick
import "Strings.js" as Strings
import "PhoneState.js" as State

Column {
    id: row
    required property var api
    required property var device
    property bool busy: false
    signal actionRequested(string action, string identifier, var payload)
    width: parent.width
    spacing: 6

    function act(action, payload) { actionRequested(action, device.id, payload || ({})); }

    Rectangle {
        width: parent.width; height: 40
        radius: row.api.radius
        color: Qt.alpha(row.api.foreground, 0.04)
        border.width: 1; border.color: Qt.alpha(row.api.foreground, 0.15)
        PhoneLabel {
            api: row.api; x: 10; anchors.verticalCenter: parent.verticalCenter
            text: State.glyph(row.device.type)
            font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 18; opacity: 0.72
        }
        Column {
            x: 36; width: parent.width - x - deviceButton.width - 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            PhoneLabel {
                api: row.api; width: parent.width
                text: row.device.name; wrapMode: Text.NoWrap; elide: Text.ElideRight
            }
            PhoneLabel {
                api: row.api; width: parent.width
                font.pixelSize: row.api.captionSize; opacity: 0.72
                wrapMode: Text.NoWrap; elide: Text.ElideRight
                text: Strings.tr(row.device.incoming ? "Pairing request" : row.device.paired ? "Offline"
                    : row.device.outgoing ? "Waiting for phone" : "Available")
            }
        }
        PhoneButton {
            id: deviceButton
            objectName: "device-action"
            api: row.api; flat: true
            anchors.right: parent.right; anchors.rightMargin: 4
            anchors.verticalCenter: parent.verticalCenter
            height: 28
            visible: !row.device.incoming
            text: Strings.tr(row.device.paired ? "Unpair" : "Pair")
            available: !row.busy && (row.device.paired || (row.device.reachable && !row.device.outgoing))
            onClicked: {
                if (row.device.paired) unpair.confirming = true;
                else row.act("pair");
            }
        }
    }
    PhoneLabel {
        api: row.api; width: parent.width
        visible: row.device.incoming
        font.pixelSize: row.api.captionSize; opacity: 0.72
        text: Strings.tr("Accept only if this is your phone. Compare the pairing code on both devices.")
    }
    PhoneLabel {
        objectName: "pairing-code"
        api: row.api; width: parent.width
        visible: (row.device.incoming || row.device.outgoing) && !!row.device.verification
        text: row.device.verification || ""
        font.pixelSize: row.api.captionSize; wrapMode: Text.WrapAnywhere
    }
    Flow {
        width: parent.width; spacing: 6
        visible: row.device.incoming
        PhoneButton {
            objectName: "accept-pairing"
            api: row.api; text: Strings.tr("Accept"); available: !row.busy
            onClicked: row.act("accept")
        }
        PhoneButton {
            objectName: "reject-pairing"
            api: row.api; text: Strings.tr("Reject"); available: !row.busy
            onClicked: row.act("reject")
        }
    }
    PhoneUnpair {
        id: unpair
        api: row.api; width: parent.width; busy: row.busy
        visible: confirming
        onConfirmed: row.act("unpair", {confirmed: true})
    }
}
