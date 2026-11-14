import QtQuick

// A dropdown whose choices open inside the panel, below the field: a separate popup
// would land outside the panel, and a click there closes the panel.
Column {
    id: control
    required property var api
    property int currentIndex: 0
    property bool expanded: false
    readonly property int count: 10
    signal activated(int index)
    spacing: 4
    opacity: enabled ? 1 : 0.5
    onEnabledChanged: if (!enabled) expanded = false
    Accessible.name: "Cities on the bar"

    Rectangle {
        id: field
        width: 88; height: 32
        radius: control.api.radius
        color: Qt.alpha(control.api.foreground, fieldHover.hovered ? 0.10 : 0.04)
        border.color: control.activeFocus || control.expanded ? control.api.accent : Qt.alpha(control.api.foreground, 0.15)
        Text {
            x: 8; anchors.verticalCenter: parent.verticalCenter
            text: control.currentIndex + 1
            color: control.api.foreground
            font.family: control.api.fontFamily
            font.pixelSize: control.api.bodySize
        }
        Text {
            x: parent.width - width - 10; anchors.verticalCenter: parent.verticalCenter
            text: "⌄"
            rotation: control.expanded ? 180 : 0
            color: control.api.foreground
        }
        HoverHandler { id: fieldHover }
        TapHandler { onTapped: control.expanded = !control.expanded }
    }

    Grid {
        visible: control.expanded
        columns: 5
        spacing: 4
        Repeater {
            model: control.count
            Rectangle {
                id: choice
                required property int index
                width: 32; height: 28
                radius: control.api.radius
                color: Qt.alpha(control.api.foreground, choiceHover.hovered || control.currentIndex === choice.index ? 0.10 : 0.04)
                border.color: control.currentIndex === choice.index ? control.api.accent : "transparent"
                Text {
                    anchors.centerIn: parent
                    text: choice.index + 1
                    color: control.currentIndex === choice.index ? control.api.accent : control.api.foreground
                    font.family: control.api.fontFamily
                    font.pixelSize: control.api.bodySize
                }
                HoverHandler { id: choiceHover }
                TapHandler {
                    onTapped: {
                        control.expanded = false;
                        control.activated(choice.index);
                    }
                }
            }
        }
    }

    Keys.onEscapePressed: event => { event.accepted = control.expanded; control.expanded = false; }
}
