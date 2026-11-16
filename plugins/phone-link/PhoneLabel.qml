import QtQuick

Text {
    required property var api
    color: api.foreground
    font.family: api.fontFamily
    font.pixelSize: 13
    textFormat: Text.PlainText
    wrapMode: Text.Wrap
}
