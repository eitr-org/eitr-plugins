pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic

Loader {
    id: button
    required property var api
    property string text: ""
    property string description: text
    property bool icon: false
    property bool selected: false
    property int textAlignment: Text.AlignHCenter
    signal clicked()
    width: icon ? 32 : 80
    height: 32
    HoverHandler { id: hover }
    ToolTip {
        id: tip
        objectName: "action-tooltip"
        visible: button.icon && button.enabled && (hover.hovered || (!!button.item && button.item.activeFocus))
        delay: 500
        text: button.description
        contentItem: Text {
            text: tip.text
            textFormat: Text.PlainText
            color: button.api.foreground
            font.family: button.api.fontFamily
            font.pixelSize: 13
        }
        background: Rectangle {
            color: button.api.background
            radius: button.api.radius
            border.color: Qt.alpha(button.api.foreground, 0.18)
        }
    }
    sourceComponent: api.controls.button
    onLoaded: {
        item.text = Qt.binding(() => button.text);
        item.flat = Qt.binding(() => button.icon);
        // The button keeps 8 px on the right of its text; the same on the left centres a glyph.
        item.textInset = 8;
        item.textSize = Qt.binding(() => button.icon ? 16 : 13);
        item.selected = Qt.binding(() => button.selected);
        item.textAlignment = Qt.binding(() => button.textAlignment);
        item.available = Qt.binding(() => button.enabled);
        item.Accessible.name = Qt.binding(() => button.description);
        item.clicked.connect(() => button.clicked());
    }
}
