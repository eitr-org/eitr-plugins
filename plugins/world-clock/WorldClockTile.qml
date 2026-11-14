import QtQuick

Item {
    required property var api
    Component.onCompleted: api.detail = "Choose cities and labels"
}
