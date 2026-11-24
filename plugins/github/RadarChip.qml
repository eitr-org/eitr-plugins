import QtQuick

Rectangle {
    id: chip
    required property var api
    required property string label
    property color ink: api.foreground
    property int maxWidth: 190
    implicitHeight: 16
    implicitWidth: Math.min(maxWidth, caption.implicitWidth + 10)
    radius: Math.min(api.radius, 4)
    color: Qt.alpha(ink, 0.13)

    RadarText {
        id: caption
        api: chip.api
        anchors.fill: parent
        anchors.leftMargin: 5
        anchors.rightMargin: 5
        verticalAlignment: Text.AlignVCenter
        font.pixelSize: Math.max(10, api.captionSize - 1)
        color: chip.ink
        text: chip.label
        elide: Text.ElideRight
    }
}
