import QtQuick
import QtQuick.Controls.Basic as Controls

Controls.ToolTip {
    id: tip
    required property var api
    delay: 450
    padding: 7

    background: Rectangle {
        color: Qt.alpha(tip.api.background, 1)
        border.color: Qt.alpha(tip.api.foreground, 0.24)
        radius: tip.api.radius
    }
    contentItem: RadarText {
        api: tip.api
        text: tip.text
        font.pixelSize: api.captionSize
        width: Math.min(320, implicitWidth)
        wrapMode: Text.Wrap
    }
}
