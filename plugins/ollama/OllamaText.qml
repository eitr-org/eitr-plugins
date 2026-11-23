import QtQuick
Text {
    required property var api
    property bool caption: false
    property bool heading: false
    color: api.foreground
    opacity: caption ? 0.72 : 1
    font.family: api.fontFamily
    font.pixelSize: heading ? 16 : caption ? 12 : 13
    font.bold: heading
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
}
