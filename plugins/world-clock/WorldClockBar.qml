import QtQuick
import "WorldClockState.js" as State

Item {
    id: bar
    required property var api
    readonly property var status: State.latest(api)
    implicitWidth: label.implicitWidth
    implicitHeight: label.text ? 24 : 0
    Text {
        id: label
        anchors.centerIn: parent
        text: bar.status ? bar.status.cities.slice(0, bar.status.barCount).map(city =>
            city.label + " " + State.time(city, bar.api.clockFormat)).join(" · ") : ""
        textFormat: Text.PlainText
        color: bar.api.foreground
        font.family: bar.api.fontFamily
        font.pixelSize: bar.api.captionSize
        font.features: ({"tnum": 1})
    }
}
