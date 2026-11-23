import QtQuick
Loader {
    id: control
    required property var api
    property string text: ""
    signal clicked()
    width: Math.max(68, metrics.advanceWidth + 24)
    height: 32
    sourceComponent: api.controls.button
    TextMetrics { id: metrics; text: control.text; font.family: control.api.fontFamily; font.pixelSize: 13 }
    onLoaded: {
        item.textSize = 13;
        item.text = Qt.binding(() => control.text);
        item.available = Qt.binding(() => control.enabled);
        item.clicked.connect(() => control.clicked());
    }
}
