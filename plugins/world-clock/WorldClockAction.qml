pragma ComponentBehavior: Bound
import QtQuick

Loader {
    id: action
    required property var api
    required property string glyph
    required property string description
    signal clicked()
    width: 24; height: 24
    anchors.verticalCenter: parent.verticalCenter
    sourceComponent: api.controls.button
    onLoaded: {
        item.icon = true;
        item.text = Qt.binding(() => action.glyph);
        item.available = Qt.binding(() => action.enabled);
        item.Accessible.role = Accessible.Button;
        item.Accessible.name = Qt.binding(() => action.description);
        item.clicked.connect(() => action.clicked());
    }
}
