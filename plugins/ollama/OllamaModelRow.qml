import QtQuick
import "OllamaState.js" as State
import "Strings.js" as Strings
Item {
    id: row
    required property var api
    required property var model
    property bool loaded: false
    property bool available: true
    signal actionRequested(string action, string name)
    height: Math.max(48, details.implicitHeight + 12)
    Column {
        id: details
        width: parent.width - action.width - 12
        anchors.verticalCenter: parent.verticalCenter
        spacing: 3
        OllamaText { api: row.api; width: parent.width; text: row.model.name; elide: Text.ElideRight; wrapMode: Text.NoWrap }
        OllamaText {
            api: row.api; width: parent.width; caption: true
            text: row.loaded ? (row.model.vram !== undefined
                ? State.size(row.model.vram) + " VRAM · " + State.size(row.model.ram) + " RAM"
                : State.size(row.model.size) + " · " + Strings.tr("Memory split unavailable"))
                : State.size(row.model.size) + " · " + (row.model.modified ? row.model.modified.slice(0, 10) : "—")
        }
    }
    OllamaButton {
        id: action
        api: row.api; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
        text: Strings.tr(row.loaded ? "Unload" : "Delete")
        enabled: row.available
        onClicked: row.actionRequested(row.loaded ? "unload" : "delete", row.model.name)
    }
}
