import QtQuick

// Sized like Eitr's panel switch: a 38×24 pill track whose round thumb carries a
// check when on and a cross when off, inside a 42×32 control.
Item {
    id: control
    required property var api
    property bool checked: false
    property string description: ""
    readonly property bool accentIsLight: api.accent.r * 0.299 + api.accent.g * 0.587 + api.accent.b * 0.114 > 0.55
    signal toggled()
    implicitWidth: 42
    implicitHeight: 32
    activeFocusOnTab: true
    Accessible.role: Accessible.CheckBox
    Accessible.checked: checked
    Accessible.name: description
    Keys.onSpacePressed: if (enabled) toggled()
    Keys.onReturnPressed: if (enabled) toggled()

    Rectangle {
        id: track
        y: (control.height - height) / 2
        width: 38; height: 24; radius: 12
        opacity: control.enabled ? 1 : 0.45
        color: control.checked ? control.api.accent : Qt.alpha(control.api.foreground, 0.12)
        border.width: control.checked ? 0 : 1
        border.color: Qt.alpha(control.api.foreground, 0.4)
        Rectangle {
            anchors.centerIn: thumb
            width: 34; height: 34; radius: 17
            color: Qt.alpha(control.checked ? control.api.accent : control.api.foreground, 0.1)
            visible: (hover.hovered || control.activeFocus) && control.enabled
        }
        Rectangle {
            id: thumb
            readonly property real size: control.checked ? 20 : 16
            x: control.checked ? track.width - 12 - size / 2 : 12 - size / 2
            anchors.verticalCenter: parent.verticalCenter
            width: size; height: size; radius: size / 2
            color: control.checked ? (control.accentIsLight ? "#1d1d1d" : "#ffffff") : Qt.alpha(control.api.foreground, 0.62)
            Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
            Text {
                anchors.centerIn: parent
                text: control.checked ? "\u{F012C}" : "\u{F0156}"
                textFormat: Text.PlainText
                color: control.checked ? control.api.accent : (control.api.foreground.hslLightness > 0.5 ? "#1d1d1d" : "#ffffff")
                font.family: control.api.fontFamily
                font.pixelSize: control.checked ? 13 : 11
            }
        }
    }
    MouseArea {
        id: hover
        readonly property bool hovered: containsMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (control.enabled) control.toggled()
    }
}
