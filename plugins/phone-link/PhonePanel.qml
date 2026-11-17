import QtQuick
import Quickshell
import Quickshell.Io
import "Strings.js" as Strings
import "PhoneState.js" as State

Item {
    id: panel
    required property var api
    property var status: null
    property string feedback: ""
    property string selectedDevice: ""
    property string currentAction: ""
    property var payload: ({})
    readonly property string actionScript: decodeURIComponent(Qt.resolvedUrl("action.py").toString().replace(/^file:\/\//, ""))
    readonly property var devices: status ? status.devices : []
    readonly property string state: status ? status.state : "loading"
    readonly property var connectedDevices: devices.filter(device => device.paired && device.reachable)
    readonly property var otherDevices: devices.filter(device => !device.paired || !device.reachable)
    implicitWidth: 380
    implicitHeight: body.implicitHeight

    function update(line) {
        const parsed = State.parse(line);
        if (parsed !== null) status = parsed;
    }
    Component.onCompleted: update(api.streamLine || api.dataText || "")
    Connections {
        target: panel.api
        function onStreamReceived(line) { panel.update(line); }
        function onDataTextChanged() { panel.update(panel.api.dataText); }
    }
    function run(action, identifier, data) {
        if (command.running) return;
        feedback = "";
        currentAction = action;
        selectedDevice = identifier;
        payload = action === "clipboard" ? {text: Quickshell.clipboardText}
            : action === "send" ? {title: Strings.tr("Send files")} : data || ({});
        command.stdinEnabled = true;
        command.command = ["python3", actionScript, action].concat(identifier ? [identifier] : []);
        command.running = true;
    }
    Process {
        id: command
        stdinEnabled: true
        onStarted: { write(JSON.stringify(panel.payload)); stdinEnabled = false; panel.payload = ({}); }
        stdout: StdioCollector { id: result }
        stderr: StdioCollector { }
        onExited: function(exitCode, exitStatus) {
            let success = false;
            let cancelled = false;
            try {
                const response = JSON.parse(result.text);
                success = exitCode === 0 && response.ok === true;
                cancelled = response.cancelled === true;
            } catch (error) { }
            panel.feedback = cancelled ? "" : Strings.tr(success
                ? ["start", "unpair", "browse"].indexOf(panel.currentAction) !== -1 ? "Done." : "Request sent. Check your phone."
                : "Action failed. Check the phone, permissions and KDE Connect.");
            panel.api.runDataCommand();
        }
    }
    Column {
        id: body
        width: parent.width; spacing: 12
        PhoneLabel {
            api: panel.api; width: parent.width
            text: "Phone Link"; font.pixelSize: panel.api.headingSize; font.bold: true
        }
        PhoneLabel {
            api: panel.api; width: parent.width
            objectName: "setup-help"
            visible: panel.connectedDevices.length === 0
            text: Strings.tr(panel.state === "loading" ? "Checking KDE Connect…"
                : panel.state === "missing" ? "Install KDE Connect through the plugin's package review."
                : panel.state === "stopped" ? "KDE Connect is not running. Start it to discover phones on your local network."
                : panel.state === "unavailable" ? "KDE Connect is not answering. Check the session D-Bus and try again."
                : "Open KDE Connect on your phone and join the same local network.")
            font.pixelSize: panel.api.captionSize; opacity: 0.72
        }
        PhoneButton {
            api: panel.api
            visible: panel.state === "stopped"
            text: Strings.tr("Start KDE Connect"); available: !command.running
            onClicked: panel.run("start", "", {})
        }
        PhoneLabel {
            api: panel.api; width: parent.width
            visible: panel.state === "ready" && panel.devices.length === 0
            text: Strings.tr("No devices found. Keep the phone app open for discovery.")
        }
        Column {
            width: parent.width; spacing: 16
            Repeater {
                model: panel.connectedDevices
                PhoneConnected {
                    required property var modelData
                    api: panel.api; device: modelData
                    busy: command.running
                    onActionRequested: function(action, identifier, data) { panel.run(action, identifier, data); }
                }
            }
        }
        Column {
            objectName: "other-devices"
            width: parent.width; spacing: 6
            visible: panel.otherDevices.length > 0
            Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.api.foreground, 0.12) }
            Item { width: 1; height: 6 }
            PhoneLabel {
                api: panel.api; width: parent.width
                text: Strings.tr("Other devices"); font.pixelSize: panel.api.captionSize; opacity: 0.72
            }
            Repeater {
                model: panel.otherDevices
                PhoneDevice {
                    required property var modelData
                    api: panel.api; device: modelData
                    busy: command.running
                    onActionRequested: function(action, identifier, data) { panel.run(action, identifier, data); }
                }
            }
        }
        PhoneLabel {
            api: panel.api; width: parent.width
            visible: panel.status !== null && (panel.status.partial || panel.status.total > panel.devices.length)
            text: Strings.tr("Some devices could not be shown. Open KDE Connect for the complete list.")
            font.pixelSize: panel.api.captionSize; opacity: 0.72
        }
        PhoneLabel {
            api: panel.api; width: parent.width
            visible: command.running || panel.feedback !== ""
            text: command.running ? Strings.tr(panel.currentAction === "send" ? "Choose files in the desktop dialog…" : "Working…") : panel.feedback
            font.pixelSize: panel.api.captionSize
        }
        PhoneLabel {
            objectName: "firewall-help"
            api: panel.api; width: parent.width
            visible: panel.connectedDevices.length === 0 && (panel.state !== "ready" || panel.devices.length === 0)
            text: Strings.tr("Eitr's firewall already lets KDE Connect through on your local network.")
            font.pixelSize: panel.api.captionSize; opacity: 0.72
        }
    }
}
