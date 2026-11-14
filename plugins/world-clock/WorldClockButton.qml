import QtQuick

// A text button, or a 24×24 glyph button when only `glyph` is set, drawn like Eitr's
// panel buttons: a subtle foreground border, a hover fill and no colour of its own.
Rectangle {
    id: button
    required property var api
    property string text: ""
    property string glyph: ""
    property string description: text
    readonly property bool iconOnly: text === ""
    readonly property bool hovered: hover.hovered
    signal clicked()

    implicitWidth: iconOnly ? 24 : label.implicitWidth + 24
    implicitHeight: iconOnly ? 24 : 28
    radius: api.radius
    color: Qt.alpha(api.foreground, !enabled ? 0.02 : hover.hovered || activeFocus ? 0.12 : iconOnly ? 0 : 0.04)
    border.width: iconOnly ? 0 : 1
    border.color: Qt.alpha(api.foreground, 0.15)
    opacity: enabled ? 1 : 0.5
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: description
    Keys.onReturnPressed: if (enabled) clicked()
    Keys.onEnterPressed: if (enabled) clicked()
    Keys.onSpacePressed: if (enabled) clicked()

    Text {
        id: label
        anchors.centerIn: parent
        text: button.iconOnly ? button.glyph : button.text
        textFormat: Text.PlainText
        color: button.api.foreground
        font.family: button.api.fontFamily
        font.pixelSize: button.iconOnly ? 15 : button.api.bodySize
    }
    // A MouseArea, not handlers: the host panel's own MouseArea would otherwise set the cursor.
    MouseArea {
        id: hover
        readonly property bool hovered: containsMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: button.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (button.enabled) button.clicked()
    }
}
