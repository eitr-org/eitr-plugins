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
    Row {
        spacing: 6
        RadioAction {
            api: now.api; text: Strings.tr("Stop")
            enabled: now.backend.playing !== null && !now.backend.busy
            onClicked: now.backend.action("stop")
        }
        RadioAction {
            api: now.api; icon: true; text: "−"; description: Strings.tr("Lower volume")
            enabled: !now.backend.busy && now.backend.volume > 0
            onClicked: now.backend.action("volume", Math.max(0, now.backend.volume - 5))
        }
        Text {
            width: 58; height: 32
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            text: now.backend.volume + "%"
            color: now.api.foreground
            font.family: now.api.fontFamily
            font.pixelSize: 12
            Accessible.name: Strings.tr("Player volume") + " " + text
        }
        RadioAction {
            api: now.api; icon: true; text: "+"; description: Strings.tr("Raise volume")
            enabled: !now.backend.busy && now.backend.volume < 100
            onClicked: now.backend.action("volume", Math.min(100, now.backend.volume + 5))
        }
    }
}
