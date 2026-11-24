import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: heading
    required property var api
    required property string text
    Layout.fillWidth: true
    spacing: 7

    Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: 5
        Layout.preferredHeight: 1
        color: Qt.alpha(heading.api.foreground, 0.12)
    }
    RadarText {
        api: heading.api
        text: heading.text
        font.bold: true
    }
}
