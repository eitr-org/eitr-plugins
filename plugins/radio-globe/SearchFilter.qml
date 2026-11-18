pragma ComponentBehavior: Bound
import QtQuick
import "Strings.js" as Strings

// The search filter's menu: what the search field looks for, one shared button per choice
// with the current one selected. The panel places it under the filter button.
Rectangle {
    id: menu
    required property var api
    required property string mode
    signal chosen(string mode)
    readonly property var choices: [{mode: "name", label: "Name"}, {mode: "tag", label: "Tag"}, {mode: "country", label: "Country"}]
    width: 160
    height: content.implicitHeight + 16
    radius: api.radius
    color: api.background
    border.color: Qt.alpha(api.foreground, 0.18)
    Column {
        id: content
        x: 8; y: 8; width: parent.width - 16
        spacing: 4
        Text {
            width: parent.width
            text: Strings.tr("Search by")
            textFormat: Text.PlainText
            color: menu.api.foreground
            opacity: 0.6
            font.family: menu.api.fontFamily
            font.pixelSize: 11
            bottomPadding: 2
        }
        Repeater {
            model: menu.choices
            RadioAction {
                required property var modelData
                objectName: "filter-" + modelData.mode
                api: menu.api
                width: content.width; height: 30
                text: Strings.tr(modelData.label)
                textAlignment: Text.AlignLeft
                selected: menu.mode === modelData.mode
                onClicked: menu.chosen(modelData.mode)
            }
        }
    }
}
