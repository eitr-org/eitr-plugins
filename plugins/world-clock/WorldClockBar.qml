import QtQuick
import "WorldClockState.js" as State

Item {
    id: bar
    required property var api
    readonly property var status: State.latest(api)
    readonly property bool empty: !bar.status || bar.status.cities.length === 0 || bar.status.barCount === 0
    // With no cities chosen yet, a globe keeps the item visible so a click opens the panel.
    implicitWidth: empty ? 24 : label.implicitWidth
    clip: true
    implicitHeight: 24
    Text {
        anchors.centerIn: parent
        visible: bar.empty
        text: "\u{F01E7}"
        textFormat: Text.PlainText
        color: bar.api.foreground
        font.family: bar.api.fontFamily
        font.pixelSize: 16
    }
    Text {
        id: label
        width: bar.width
        elide: Text.ElideRight
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        visible: !bar.empty
        text: !bar.empty ? bar.status.cities.slice(0, bar.status.barCount).map(city =>
            (city.flag ? city.flag + " " : "") + city.label + " " + State.time(city, bar.api.clockFormat)).join(" · ") : ""
        textFormat: Text.PlainText
        color: bar.api.foreground
        font.family: bar.api.fontFamily
        // Bar text matches the clock and weather beside it: bold, at the host's bar size.
        font.pixelSize: bar.api.barTextSize || 14
        font.bold: true
        font.features: ({"tnum": 1})
    }
}
