import QtQuick

Text {
    required property var api
    color: api.foreground
    font.family: api.fontFamily
    font.pixelSize: api.bodySize
    textFormat: Text.PlainText
}
