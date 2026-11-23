import QtQuick
import "Strings.js" as Strings
import "OllamaState.js" as State
Item {
    id: root
    required property var api
    readonly property var snapshot: State.parse(api.dataText)
    readonly property var loaded: snapshot ? snapshot.loaded : []
    readonly property bool downloading: snapshot !== null && snapshot.pull.state === "downloading"
    readonly property string loadedNames: loaded.map(model => model.name).join(", ")
    readonly property string detail: loadedNames + (downloading
        ? (loadedNames ? " · " : "") + Strings.tr("Downloading") + " · " + (snapshot.pull.model || "") : "")
    implicitWidth: 24
    implicitHeight: 24
    Accessible.name: "Ollama"
    Accessible.description: detail
    onDetailChanged: api.detail = detail
    Component.onCompleted: api.detail = detail
    // The same 15 px glyph size as Eitr's own status icons.
    Text {
        anchors.centerIn: parent
        text: "\u{F061A}"
        color: root.api.foreground
        font.family: root.api.fontFamily; font.pixelSize: 15
    }
    Rectangle {
        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3
        width: 6; height: 6; radius: 3
        visible: root.loaded.length > 0 || root.downloading
        color: root.api.accent
        border.width: 1; border.color: root.api.background
    }
}
