import QtQuick

Item {
    id: control
    required property var api
    property string text: ""
    property bool available: true
    property bool selected: false
    signal clicked()
    implicitWidth: Math.max(68, labelSize.advanceWidth + 20)
    implicitHeight: 32
    width: implicitWidth
    height: implicitHeight
    TextMetrics { id: labelSize; text: control.text; font.family: control.api.fontFamily; font.pixelSize: 13 }
    Loader {
        anchors.fill: parent
        sourceComponent: control.api.controls.button
        onLoaded: {
            item.text = Qt.binding(() => control.text);
            item.available = Qt.binding(() => control.available);
            item.selected = Qt.binding(() => control.selected);
            item.clicked.connect(() => control.clicked());
        }
    }
}
