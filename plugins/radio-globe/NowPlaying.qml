pragma ComponentBehavior: Bound
import QtQuick
import "Strings.js" as Strings

Column {
    id: now
    required property var api
    required property var backend
    spacing: 4
    Text {
        width: parent.width
        text: now.backend.playing ? Strings.tr("Now playing") + " · " + now.backend.playing.station.name : Strings.tr("Choose a station to listen")
        textFormat: Text.PlainText
        elide: Text.ElideRight
        color: now.api.foreground
        font.family: now.api.fontFamily
        font.pixelSize: 13
    }
    RadioAction {
        api: now.api; text: Strings.tr("Stop")
        enabled: now.backend.playing !== null && !now.backend.busy
        onClicked: now.backend.action("stop")
    }
}
