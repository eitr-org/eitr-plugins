import QtQuick

// Eitr's own panel button (api.controls.button): a text button, or a glyph button when
// only `glyph` is set.
Item {
    id: button
    required property var api
    property string text: ""
    property string glyph: ""
    property string description: text
    readonly property bool iconOnly: text === ""
    readonly property bool hovered: hover.hovered
    signal clicked()

    implicitWidth: iconOnly ? 28 : Math.max(68, labelSize.advanceWidth + 20)
    implicitHeight: iconOnly ? 28 : 32
    width: implicitWidth
    height: implicitHeight
    TextMetrics { id: labelSize; text: button.text; font.family: button.api.fontFamily; font.pixelSize: button.api.bodySize }
    HoverHandler { id: hover }
    Loader {
        anchors.fill: parent
        sourceComponent: button.api.controls.button
        onLoaded: {
            item.icon = Qt.binding(() => button.iconOnly);
            item.iconSize = 16;
            item.text = Qt.binding(() => button.iconOnly ? button.glyph : button.text);
            item.available = Qt.binding(() => button.enabled);
            item.Accessible.name = Qt.binding(() => button.description);
            item.clicked.connect(() => button.clicked());
        }
    }
}
