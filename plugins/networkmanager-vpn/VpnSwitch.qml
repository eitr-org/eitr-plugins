import QtQuick

// Eitr's own panel switch (api.controls.toggle). `checked` follows the profile's real state:
// a click only asks for the change, and the switch moves when the status says it happened.
Item {
    id: control
    required property var api
    property bool checked: false
    property string description: ""
    signal toggled()
    implicitWidth: 42
    implicitHeight: 32
    Loader {
        anchors.fill: parent
        sourceComponent: control.api.controls.toggle
        onLoaded: {
            item.checked = Qt.binding(() => control.checked);
            item.enabled = Qt.binding(() => control.enabled);
            item.Accessible.name = Qt.binding(() => control.description);
            item.toggled.connect(() => {
                control.toggled();
                item.checked = Qt.binding(() => control.checked);
            });
        }
    }
}
