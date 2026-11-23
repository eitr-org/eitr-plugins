pragma ComponentBehavior: Bound
import QtQuick
import Quickshell.Io
import "OllamaState.js" as State
import "Strings.js" as Strings
Item {
    id: panel
    required property var api
    readonly property var snapshot: State.parse(api.dataText)
    readonly property bool configured: snapshot !== null && snapshot.ready
    readonly property bool running: snapshot !== null && snapshot.running
    readonly property var progress: snapshot ? snapshot.pull : ({})
    readonly property bool pulling: progress.state === "downloading"
    property string pendingDelete: ""
    property string feedback: ""
    readonly property string actionScript: decodeURIComponent(Qt.resolvedUrl("action.py").toString().replace(/^file:\/\//, ""))
    implicitWidth: 410
    implicitHeight: body.implicitHeight
    function run(action, name) {
        if (operation.running) return;
        feedback = "";
        operation.command = ["python3", actionScript, action].concat(name ? [name] : []);
        operation.running = true;
    }
    Process {
        id: operation
        stdout: StdioCollector {}
        onExited: (exitCode, exitStatus) => {
            panel.feedback = Strings.tr(exitCode === 0 ? "Done" : "Operation failed. Check the service and model name.");
            if (panel.api.observed) panel.api.runDataCommand();
        }
    }
    Column {
        id: body
        width: parent.width
        spacing: 14
        Row {
            width: parent.width
            spacing: 10
            Column {
                width: parent.width - service.width - 10
                spacing: 3
                OllamaText { api: panel.api; heading: true; text: "Ollama" }
                OllamaText {
                    api: panel.api; caption: true
                    text: Strings.tr(!panel.snapshot ? "Checking status…" : !panel.configured ? "Setup needed" : panel.running ? "Running" : "Stopped")
                }
            }
            OllamaButton {
                id: service
                api: panel.api
                text: Strings.tr(!panel.configured ? "Set up" : panel.running ? "Stop" : "Start")
                enabled: panel.snapshot !== null && !operation.running && !panel.pulling
                onClicked: panel.run(!panel.configured ? "setup" : panel.running ? "stop" : "start", "")
            }
        }
        OllamaText {
            api: panel.api; width: parent.width; caption: true
            visible: panel.snapshot !== null && !panel.configured
            text: Strings.tr("Choose Ollama in Eitr’s Default Assistant setup. It installs and configures the local assistant after confirmation.")
        }
        OllamaText {
            api: panel.api; width: parent.width; caption: true
            visible: panel.configured
            text: Strings.tr("Eitr’s local model:") + " " + (panel.snapshot ? panel.snapshot.defaultModel : "qwen3:4b") + "\n" + Strings.tr("Eitr does not offer a model chooser yet.")
        }
        OllamaText {
            api: panel.api; width: parent.width; caption: true
            visible: text !== ""
            text: panel.feedback || (panel.api.dataError || panel.snapshot && panel.snapshot.error ? Strings.tr("Status unavailable. Check the user service.") : "")
        }
        Column {
            width: parent.width; spacing: 6; visible: panel.configured && panel.running
            OllamaText { api: panel.api; heading: true; text: Strings.tr("Loaded models") }
            OllamaText {
                api: panel.api; caption: true
                visible: panel.snapshot !== null && panel.snapshot.loaded.length === 0
                text: Strings.tr("No models loaded")
            }
            Repeater {
                model: panel.snapshot ? panel.snapshot.loaded : []
                OllamaModelRow {
                    required property var modelData
                    width: parent.width; api: panel.api; model: modelData; loaded: true
                    available: !operation.running
                    onActionRequested: (action, name) => panel.run(action, name)
                }
            }
        }
        Column {
            width: parent.width; spacing: 6; visible: panel.configured && panel.running
            OllamaText { api: panel.api; heading: true; text: Strings.tr("Installed models") }
            OllamaText {
                api: panel.api; caption: true
                visible: panel.snapshot !== null && panel.snapshot.installed.length === 0
                text: Strings.tr("No installed models")
            }
            Repeater {
                model: panel.snapshot ? panel.snapshot.installed : []
                OllamaModelRow {
                    required property var modelData
                    width: parent.width; api: panel.api; model: modelData
                    available: !operation.running && !panel.pulling
                    onActionRequested: (action, name) => panel.pendingDelete = name
                }
            }
        }
        Column {
            width: parent.width; spacing: 8; visible: panel.pendingDelete !== ""
            OllamaText {
                api: panel.api; width: parent.width
                text: Strings.tr("Delete model?") + " " + panel.pendingDelete + "\n" + Strings.tr("This removes its local download. Download it again to restore it.")
                    + (panel.snapshot && panel.pendingDelete === panel.snapshot.defaultModel ? "\n" + Strings.tr("This is Eitr’s local model. Local chat will need setup again.") : "")
            }
            Row {
                spacing: 8
                OllamaButton {
                    api: panel.api; text: Strings.tr("Confirm delete"); enabled: !operation.running && panel.running && !panel.pulling
                    onClicked: { panel.run("delete-confirmed", panel.pendingDelete); panel.pendingDelete = ""; }
                }
                OllamaButton { api: panel.api; text: Strings.tr("Cancel"); onClicked: panel.pendingDelete = "" }
            }
        }
        Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.api.foreground, 0.12); visible: panel.configured }
        OllamaDownload {
            width: parent.width; visible: panel.configured
            api: panel.api; progress: panel.progress; available: panel.running; busy: operation.running
            installed: panel.snapshot ? panel.snapshot.installed.map(model => model.name) : []
            onActionRequested: (action, name) => panel.run(action, name)
        }
        OllamaButton {
            api: panel.api; text: Strings.tr("Open Chat"); visible: panel.configured
            enabled: !operation.running
            onClicked: panel.run("chat", "")
        }
        OllamaText {
            api: panel.api; width: parent.width; caption: true; visible: panel.configured
            text: Strings.tr("Opens your default assistant, just like SUPER + A.")
        }
    }
}
