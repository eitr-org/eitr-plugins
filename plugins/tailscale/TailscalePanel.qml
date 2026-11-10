pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Eitr as Eitr
import "TailscaleState.js" as TailscaleState

// The Tailscale panel: the connection switch (or the first setup step) in the heading,
// guidance while something is missing, this computer's details, then every device on
// the tailnet with Taildrop and copy actions. Actions run this plugin's action.py
// detached, with explicit argv; steps needing a password or browser open a terminal.
Item {
    id: panel
    required property var api
    property var status: null
    property string copiedAddress: ""
    property string pendingAction: ""
    readonly property string actionScript: decodeURIComponent(Qt.resolvedUrl("action.py").toString().replace(/^file:\/\//, ""))
    readonly property string connectionState: status ? status.state : ""
    readonly property bool switchable: ["connected", "disconnected", "starting"].indexOf(connectionState) !== -1
    readonly property bool connected: connectionState === "connected"
    readonly property var peers: status && status.peers ? status.peers : []
    readonly property string firstStep: connectionState === "not-installed" || connectionState === "unavailable" ? "setup"
        : connectionState === "signed-out" ? "login" : ""
    readonly property string guidance: {
        if (connectionState === "not-installed") return Eitr.I18n.tr("Set up installs Tailscale and starts its service through Eitr's Remote Access setup.");
        if (connectionState === "unavailable") return Eitr.I18n.tr("The Tailscale service is not answering. Set up starts it again.");
        if (connectionState === "signed-out") return Eitr.I18n.tr("Sign in opens the Tailscale sign-in page in your browser to join your tailnet.");
        if (connectionState === "needs-approval") return Eitr.I18n.tr("This computer is waiting for approval in the Tailscale admin console.");
        return "";
    }
    readonly property bool needsOperator: status !== null && status.operator === false && firstStep === ""
    implicitWidth: 400
    implicitHeight: body.implicitHeight + 4

    function applyData() {
        const parsed = TailscaleState.parse(api.dataText);
        if (parsed === null) return;
        status = parsed;
        if ((pendingAction === "connect" && parsed.state === "connected")
            || (pendingAction === "disconnect" && parsed.state !== "connected" && parsed.state !== "starting")) {
            pendingAction = "";
            followUp.stop();
        }
    }
    Connections {
        target: panel.api
        function onDataTextChanged() { panel.applyData(); }
    }
    Component.onCompleted: applyData()

    function run(argumentsList) {
        Quickshell.execDetached([panel.actionScript].concat(argumentsList));
        if (argumentsList[0] !== "connect" && argumentsList[0] !== "disconnect") return;
        pendingAction = argumentsList[0];
        followUp.remaining = 5;
        followUp.restart();
    }
    function copy(address) {
        Quickshell.clipboardText = address;
        copiedAddress = address;
        copiedReset.restart();
    }
    // Connect and disconnect take a moment: check again a few times so the switch follows.
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
                TailscaleLogo {
                    anchors.centerIn: parent
                    dot: 3
                    color: panel.api.foreground
                    opacity: panel.connected ? 1 : 0.45
                }
            }
            Column {
                x: 38
                width: controls.x - x - 8
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Text {
                    width: parent.width
                    text: "Tailscale"
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: panel.api.foreground
                    font.family: panel.api.fontFamily
                    font.pixelSize: panel.api.headingSize
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: panel.pendingAction === "connect" ? Eitr.I18n.tr("Connecting…")
                        : panel.pendingAction === "disconnect" ? Eitr.I18n.tr("Disconnecting…")
                        : panel.status ? Eitr.I18n.tr(TailscaleState.stateLabels[panel.connectionState] || "Status unavailable")
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
                TailscaleButton {
                    api: panel.api
                    visible: panel.firstStep !== ""
                    text: panel.firstStep === "login" ? Eitr.I18n.tr("Sign in") : Eitr.I18n.tr("Set up")
                    onClicked: panel.run([panel.firstStep])
                }
                TailscaleSwitch {
                    api: panel.api
                    visible: panel.switchable
                    enabled: panel.pendingAction === ""
                    checked: panel.connected
                    description: Eitr.I18n.tr("Connected")
                    onToggled: panel.run([panel.connected ? "disconnect" : "connect"])
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

        Item {
            visible: panel.needsOperator
            width: parent.width
            height: visible ? Math.max(operatorText.implicitHeight, allowButton.height) : 0
            Text {
                id: operatorText
                width: parent.width - allowButton.width - 12
                anchors.verticalCenter: parent.verticalCenter
                text: Eitr.I18n.tr("Allow this account to connect, disconnect and use Taildrop without sudo.")
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: panel.api.foreground
                opacity: 0.72
                font.family: panel.api.fontFamily
                font.pixelSize: panel.api.captionSize
            }
            TailscaleButton {
                id: allowButton
                api: panel.api
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: Eitr.I18n.tr("Allow")
                onClicked: panel.run(["operator"])
            }
        }

        TailscaleDetails {
            visible: panel.status !== null && (panel.status.device || "") !== ""
            width: parent.width
            api: panel.api
            status: panel.status || ({})
            copiedAddress: panel.copiedAddress
            onCopyRequested: address => panel.copy(address)
        }

        Column {
            visible: panel.peers.length > 0
            width: parent.width
            spacing: 6
            Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.api.foreground, 0.12) }
            Text {
                topPadding: 4
                text: Eitr.I18n.tr("DEVICES")
                textFormat: Text.PlainText
                color: panel.api.foreground
                opacity: 0.72
                font.family: panel.api.fontFamily
                font.pixelSize: panel.api.captionSize
            }
            Repeater {
                model: panel.peers
                TailscalePeerRow {
                    required property var modelData
                    width: parent.width
                    api: panel.api
                    peer: modelData
                    canSend: panel.connected && modelData.taildrop === true
                    canPing: panel.connected
                    copied: panel.copiedAddress !== "" && panel.copiedAddress === modelData.address
                    onSendRequested: address => panel.run(["send-to", address])
                    onCopyRequested: address => panel.copy(address)
                    onPingRequested: address => panel.run(["ping", address])
                }
            }
        }

        // What Walker's Remote Access menu offered: a full report, and undoing Eitr's setup.
        Row {
            visible: panel.status !== null && panel.status.installed === true
            spacing: 6
            TailscaleButton {
                api: panel.api
                text: Eitr.I18n.tr("Detailed status")
                onClicked: panel.run(["status"])
            }
            TailscaleButton {
                api: panel.api
                text: Eitr.I18n.tr("Undo setup")
                description: Eitr.I18n.tr("Restore tailscaled startup and the previous operator")
                onClicked: panel.run(["undo-setup"])
            }
        }

        Item {
            visible: panel.switchable
            width: parent.width
            height: visible ? openFolder.height : 0
            Text {
                width: parent.width - openFolder.width - 12
                anchors.verticalCenter: parent.verticalCenter
                text: Eitr.I18n.tr("Files sent to this computer arrive in Documents/Taildrop.")
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: panel.api.foreground
                opacity: 0.72
                font.family: panel.api.fontFamily
                font.pixelSize: panel.api.captionSize
            }
            TailscaleButton {
                id: openFolder
                api: panel.api
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                text: Eitr.I18n.tr("Open folder")
                onClicked: panel.run(["open-folder"])
            }
        }
    }
}
