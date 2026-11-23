import QtQuick
import "OllamaState.js" as State
import "Strings.js" as Strings
Column {
    id: download
    required property var api
    required property var progress
    property bool available: true
    property bool busy: false
    property var installed: []
    readonly property bool pulling: progress.state === "downloading"
    signal actionRequested(string action, string name)
    spacing: 10
    OllamaText { api: download.api; heading: true; text: Strings.tr("Download a model") }
    // Suggestions leave out models already installed; with all of them installed, only the field shows.
    readonly property var suggestions: [
        {value: "qwen3:4b", label: "qwen3:4b · ~2.5 GB"},
        {value: "llama3.2:3b", label: "llama3.2:3b · ~2.0 GB"},
        {value: "gemma3:1b", label: "gemma3:1b · ~806 MB"}
    ]
    readonly property var offered: suggestions.filter(choice => installed.indexOf(choice.value) === -1)
    property string selected: ""
    readonly property string typed: field.item ? field.item.text.trim() : ""
    readonly property bool alreadyInstalled: typed !== "" && installed.indexOf(typed) !== -1
    function choose(value) {
        selected = value;
        if (field.item) field.item.text = value;
    }
    onOfferedChanged: if (offered.every(choice => choice.value !== selected)) choose(offered.length ? offered[0].value : "")
    Component.onCompleted: choose(offered.length ? offered[0].value : "")
    Loader {
        width: parent.width
        visible: download.offered.length > 0
        sourceComponent: download.api.controls.dropdown
        onLoaded: {
            item.width = Qt.binding(() => width);
            item.floatingLabel = Strings.tr("Suggestions");
            item.helperText = Strings.tr("Approximate downloads; sizes can change.");
            item.choices = Qt.binding(() => download.offered);
            item.current = Qt.binding(() => download.selected);
            item.chosen.connect(value => download.choose(value));
        }
    }
    Row {
        width: parent.width
        spacing: 8
        Loader {
            id: field
            width: parent.width - pull.width - 8
            height: 34
            sourceComponent: download.api.controls.textField
            enabled: download.available && !download.pulling && !download.busy
            onLoaded: {
                item.text = download.selected;
                item.placeholderText = Strings.tr("Model name, e.g. llama3.2:3b");
            }
        }
        OllamaButton {
            id: pull
            api: download.api
            text: Strings.tr("Download")
            enabled: download.available && !download.pulling && !download.busy && download.typed !== "" && !download.alreadyInstalled
            onClicked: download.actionRequested("pull", field.item.text.trim())
        }
    }
    OllamaText {
        api: download.api; width: parent.width; caption: true
        visible: download.alreadyInstalled
        text: Strings.tr("Already installed")
    }
    Column {
        width: parent.width
        visible: download.progress.state !== undefined
        spacing: 8
        OllamaText {
            api: download.api; width: parent.width; caption: true
            text: (download.progress.model || "") + " · " + Strings.tr(download.pulling ? "Downloading"
                : download.progress.state === "complete" ? "Complete"
                : download.progress.state === "cancelled" ? "Cancelled"
                : download.progress.state === "interrupted" ? "Interrupted — retry to resume" : "Download failed — retry")
        }
        Rectangle {
            width: parent.width; height: 5; radius: 2.5
            color: Qt.alpha(download.api.foreground, 0.12)
            visible: download.pulling
            Rectangle {
                height: parent.height; radius: parent.radius; color: download.api.accent
                width: parent.width * (download.progress.total > 0 ? Math.min(1, download.progress.completed / download.progress.total) : 0)
            }
        }
        Row {
            spacing: 8
            visible: download.pulling
            OllamaButton {
                api: download.api; text: Strings.tr("Cancel"); enabled: !download.busy
                onClicked: download.actionRequested("cancel", "")
            }
            OllamaText {
                api: download.api; caption: true; anchors.verticalCenter: parent.verticalCenter
                text: download.progress.total > 0 ? State.size(download.progress.completed) + " / " + State.size(download.progress.total) : Strings.tr("Preparing download…")
            }
        }
        OllamaText {
            api: download.api; width: parent.width; caption: true
            text: Strings.tr("Downloads continue when this panel closes.")
        }
    }
}
