pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Eitr as Eitr
import "WireGuardState.js" as WireGuardState

// The WireGuard panel: Import a config in the heading, the active tunnel's endpoint,
// transfer and latest handshake, imported tunnels with connect/disconnect switches,
// and inline confirmation before removing a tunnel.
Item {
    id: panel
    required property var api
    property var status: null
    property string copiedText: ""
    property string pendingAction: ""
    property string pendingTarget: ""
    property string confirmRemoveId: ""
    property string confirmRemoveName: ""
    readonly property string actionScript: decodeURIComponent(Qt.resolvedUrl("action.py").toString().replace(/^file:\/\//, ""))
    readonly property string connectionState: status ? status.state : ""
    readonly property bool connected: connectionState === "connected"
    readonly property var tunnels: status && status.tunnels ? status.tunnels : []
    readonly property string guidance: {
        if (connectionState === "not-installed") return Eitr.I18n.tr("wireguard-tools is not installed on this computer.");
        if (connectionState === "unavailable") return Eitr.I18n.tr("WireGuard status is currently unavailable.");
        if (status !== null && tunnels.length === 0) return Eitr.I18n.tr("No WireGuard tunnels are imported yet. Use Import a config to review and add a .conf file.");
        return "";
    }
    implicitWidth: 400
    implicitHeight: body.implicitHeight + 4

    function applyData() {
        const parsed = WireGuardState.parse(api.dataText);
        if (parsed === null) return;
        status = parsed;
        if (confirmRemoveId !== "" && !(parsed.tunnels || []).some(tunnel => tunnel.id === confirmRemoveId)) {
            confirmRemoveId = "";
            confirmRemoveName = "";
        }
        if (pendingAction !== "") {
            const target = (parsed.tunnels || []).find(tunnel => tunnel.id === pendingTarget);
            if ((pendingAction === "up" && target && target.connected)
                || (pendingAction === "down" && (!target || !target.connected))
                || (pendingAction === "remove" && !target)) {
                pendingAction = "";
                pendingTarget = "";
                followUp.stop();
            }
        }
    }
    Connections {
        target: panel.api
        function onDataTextChanged() { panel.applyData(); }
    }
    Component.onCompleted: applyData()

    function run(argumentsList) {
        Quickshell.execDetached([panel.actionScript].concat(argumentsList));
        if (["up", "down", "remove"].indexOf(argumentsList[0]) === -1) return;
        pendingAction = argumentsList[0];
        pendingTarget = argumentsList[1] || "";
        followUp.remaining = 6;
        followUp.restart();
    }
    function requestRemove(target, name) {
        confirmRemoveId = target;
        confirmRemoveName = name;
    }
    function cancelRemove() {
        confirmRemoveId = "";
        confirmRemoveName = "";
    }
    function confirmRemove() {
        if (confirmRemoveId === "") return;
        const target = confirmRemoveId;
        confirmRemoveId = "";
        confirmRemoveName = "";
        run(["remove", target]);
    }
    function copy(value) {
        Quickshell.clipboardText = value;
        copiedText = value;
        copiedReset.restart();
    }
    Timer {
        id: followUp
        property int remaining: 0
        interval: 1500
        repeat: true
        onTriggered: {
            remaining -= 1;
            panel.api.runDataCommand();
            if (remaining > 0) return;
            stop();
            panel.pendingAction = "";
            panel.pendingTarget = "";
        }
    }
    Timer { id: copiedReset; interval: 1500; onTriggered: panel.copiedText = "" }

    Column {
        id: body
        width: parent.width
        spacing: 14

        Item {
            width: parent.width
            height: 42
            Rectangle {
                id: seal
                anchors.verticalCenter: parent.verticalCenter
                width: 28; height: 28; radius: 14
                color: Qt.alpha(panel.api.accent, panel.connected ? 0.22 : 0.08)
                border.width: 1
                border.color: Qt.alpha(panel.api.foreground, 0.18)
                WireGuardLogo {
                    anchors.centerIn: parent
                    size: 18
                    background: panel.api.background
                    dimmed: !panel.connected
                }
            }
            Column {
                x: 38
                width: Math.max(0, controls.x - x - 8)
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    width: parent.width
                    text: "WireGuard"
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: panel.api.foreground
                    font.family: panel.api.fontFamily
                    font.pixelSize: panel.api.headingSize
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: panel.pendingAction === "up" ? Eitr.I18n.tr("Connecting…")
                        : panel.pendingAction === "down" ? Eitr.I18n.tr("Disconnecting…")
                        : panel.pendingAction === "remove" ? Eitr.I18n.tr("Removing…")
                        : panel.connected && panel.status && panel.status.activeTunnel
                            ? Eitr.I18n.tr("Connected") + " · " + panel.status.activeTunnel
                        : panel.status ? Eitr.I18n.tr(WireGuardState.stateLabels[panel.connectionState] || "Status unavailable")
                        : panel.api.dataError !== "" ? Eitr.I18n.tr("Status unavailable") : Eitr.I18n.tr("Checking status…")
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: panel.api.foreground
                    opacity: 0.72
                    font.family: panel.api.fontFamily
                    font.pixelSize: panel.api.captionSize
                }
            }
            Row {
                id: controls
                x: parent.width - width
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6
                WireGuardButton {
                    api: panel.api
                    text: Eitr.I18n.tr("Import a config")
                    onClicked: panel.run(["import"])
                }
            }
        }

        Text {
            visible: text !== ""
            width: parent.width
            text: panel.guidance
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: panel.api.foreground
            opacity: 0.72
            font.family: panel.api.fontFamily
            font.pixelSize: panel.api.captionSize
        }

        WireGuardDetails {
            visible: panel.connected && panel.status !== null
            width: parent.width
            api: panel.api
            status: panel.status || ({})
            copiedText: panel.copiedText
            onCopyRequested: value => panel.copy(value)
        }

        Column {
            visible: panel.tunnels.length > 0
            width: parent.width
            spacing: 6
            Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.api.foreground, 0.12) }
            Text {
                topPadding: 4
                text: Eitr.I18n.tr("TUNNELS")
                textFormat: Text.PlainText
                color: panel.api.foreground
                opacity: 0.72
                font.family: panel.api.fontFamily
                font.pixelSize: panel.api.captionSize
            }
            Repeater {
                model: panel.tunnels
                WireGuardTunnelRow {
                    required property var modelData
                    width: parent.width
                    api: panel.api
                    tunnel: modelData
                    switchEnabled: panel.pendingAction === ""
                    onToggleRequested: (target, shouldConnect) => panel.run([shouldConnect ? "up" : "down", target])
                    onRemoveRequested: (target, name) => panel.requestRemove(target, name)
                }
            }
        }

        Rectangle {
            visible: panel.confirmRemoveId !== ""
            width: parent.width
            height: visible ? confirmRow.implicitHeight + 16 : 0
            radius: panel.api.radius
            color: Qt.alpha(panel.api.foreground, 0.05)
            border.width: 1
            border.color: Qt.alpha(panel.api.foreground, 0.18)
            Item {
                id: confirmRow
                x: 10
                y: 8
                width: parent.width - 20
                implicitHeight: Math.max(confirmLabel.implicitHeight, confirmButtons.height)
                Text {
                    id: confirmLabel
                    width: Math.max(0, parent.width - confirmButtons.width - 12)
                    anchors.verticalCenter: parent.verticalCenter
                    text: Eitr.I18n.tr("Remove tunnel {name}?", {name: panel.confirmRemoveName})
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: panel.api.foreground
                    font.family: panel.api.fontFamily
                    font.pixelSize: panel.api.bodySize
                }
                Row {
                    id: confirmButtons
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    WireGuardButton {
                        api: panel.api
                        text: Eitr.I18n.tr("Cancel")
                        onClicked: panel.cancelRemove()
                    }
                    WireGuardButton {
                        api: panel.api
                        text: Eitr.I18n.tr("Remove")
                        onClicked: panel.confirmRemove()
                    }
                }
            }
        }
    }
}
