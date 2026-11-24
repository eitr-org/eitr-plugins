import QtQuick
import QtQuick.Layouts
import "Strings.js" as Strings

ColumnLayout {
    id: field
    required property var api
    required property string label
    required property string value
    signal save(string value)
    spacing: 4

    RadarText { api: field.api; text: field.label; Layout.fillWidth: true; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        Loader {
            id: editor
            readonly property Item fieldItem: item
            Layout.fillWidth: true
            sourceComponent: field.api.controls.textField
            onLoaded: {
                fieldItem.Accessible.name = Qt.binding(() => field.label);
                item.text = field.value;
                item.accepted.connect(function() { field.save(item.text); });
            }
        }
        RadarButton {
            api: field.api; label: Strings.tr("Save")
            onClicked: field.save(editor.item.text)
        }
    }
    onValueChanged: if (editor.item && !editor.item.activeFocus) editor.item.text = value
}
