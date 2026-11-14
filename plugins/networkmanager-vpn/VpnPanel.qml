pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Eitr as Eitr
import "VpnState.js" as VpnState

// The NetworkManager VPN panel: OpenVPN, OpenConnect and WireGuard profiles known to
// NetworkManager with connect/disconnect switches, the active profile's details, and
// Import. When the desktop uses iwd, it explains the NetworkManager backend choice and
// opens Settings > Connections > Wi-Fi > WiFi backend instead of failing.
Item {
    id: panel
    required property var api
    property var status: null
    property string copiedAddress: ""
    property string pendingAction: ""
    property string pendingTarget: ""
    readonly property string actionScript: decodeURIComponent(Qt.resolvedUrl("action.py").toString().replace(/^file:\/\//, ""))
    readonly property string connectionState: status ? status.state : ""
    readonly property bool connected: connectionState === "connected"
    readonly property bool usingIwd: connectionState === "iwd"
    readonly property var profiles: status && status.profiles ? status.profiles : []
    readonly property string guidance: {
        if (usingIwd) return Eitr.I18n.tr("NetworkManager VPN profiles need the NetworkManager backend. Choose NetworkManager in Settings > Connections > Wi-Fi > WiFi backend, then reboot. The saved choice leaves your current connection running.");
        if (connectionState === "not-installed") return Eitr.I18n.tr("NetworkManager (nmcli) is not installed on this computer.");
        if (connectionState === "unavailable") return Eitr.I18n.tr("NetworkManager status is currently unavailable.");
        if (status !== null && profiles.length === 0) return Eitr.I18n.tr("No OpenVPN, OpenConnect or WireGuard profiles are saved in NetworkManager yet. Use Import to add an .ovpn or .conf profile.");
        return "";
    }
    implicitWidth: 400
    implicitHeight: body.implicitHeight + 4

    function applyData() {
        const parsed = VpnState.parse(api.dataText);
        if (parsed === null) return;
        status = parsed;
        if (pendingAction !== "") {
            const target = (parsed.profiles || []).find(profile => profile.id === pendingTarget);
            if ((pendingAction === "up" && target && target.connected)
                || (pendingAction === "down" && (!target || !target.connected))) {
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
        if (argumentsList[0] !== "up" && argumentsList[0] !== "down") return;
        pendingAction = argumentsList[0];
        pendingTarget = argumentsList[1] || "";
        followUp.remaining = 6;
        followUp.restart();
    }
    function copy(address) {
        Quickshell.clipboardText = address;
        copiedAddress = address;
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
    Timer { id: copiedReset; interval: 1500; onTriggered: panel.copiedAddress = "" }

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
                VpnLogo {
                    anchors.centerIn: parent
                    size: 18
                    color: panel.api.foreground
                    opacity: panel.connected ? 1 : 0.45
                }
            }
            Column {
                x: 38
                width: Math.max(0, controls.x - x - 8)
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    width: parent.width
                    text: "NetworkManager VPN"
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
                        : panel.connected && panel.status && panel.status.activeProfile
                            ? Eitr.I18n.tr("Connected") + " · " + panel.status.activeProfile
                        : panel.status ? Eitr.I18n.tr(VpnState.stateLabels[panel.connectionState] || "Status unavailable")
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
                VpnButton {
                    api: panel.api
                    visible: panel.usingIwd
                    text: Eitr.I18n.tr("Open Settings")
                    onClicked: panel.run(["open-settings"])
                }
                VpnButton {
                    api: panel.api
                    visible: !panel.usingIwd && panel.connectionState !== "not-installed"
                    text: Eitr.I18n.tr("Import")
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

        VpnDetails {
            visible: panel.connected && panel.status !== null
            width: parent.width
            api: panel.api
            status: panel.status || ({})
            copiedAddress: panel.copiedAddress
            onCopyRequested: value => panel.copy(value)
        }

        Column {
            visible: panel.profiles.length > 0
            width: parent.width
            spacing: 6
            Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.api.foreground, 0.12) }
            Text {
                topPadding: 4
                text: Eitr.I18n.tr("PROFILES")
                textFormat: Text.PlainText
                color: panel.api.foreground
                opacity: 0.72
                font.family: panel.api.fontFamily
                font.pixelSize: panel.api.captionSize
            }
            Repeater {
                model: panel.profiles
                VpnProfileRow {
                    required property var modelData
                    width: parent.width
                    api: panel.api
                    profile: modelData
                    switchEnabled: panel.pendingAction === ""
                    onToggleRequested: (identifier, shouldConnect) => panel.run([shouldConnect ? "up" : "down", identifier])
                }
            }
        }
    }
}
