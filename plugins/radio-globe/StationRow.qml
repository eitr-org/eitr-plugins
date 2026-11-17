pragma ComponentBehavior: Bound
import QtQuick
import "Strings.js" as Strings

Item {
    id: row
    required property var api
    required property var station
    property bool favorite: false
    property bool playing: false
    // The last row has no divider under it.
    property bool last: false
    signal playRequested()
    signal favoriteRequested()
    // 8 px above the name keeps it clear of the divider under the previous row.
    implicitHeight: 78
    RadioAction {
        api: row.api
        y: 8
        width: parent.width - 38
        height: 28
        text: (row.playing ? "▶ " : "") + row.station.name
        description: Strings.tr("Play") + " " + row.station.name
        selected: row.playing
        onClicked: row.playRequested()
        textAlignment: Text.AlignLeft
    }
    RadioAction {
        api: row.api
        anchors.right: parent.right
        y: 8; width: 28; height: 28
        icon: true
        text: row.favorite ? "★" : "☆"
        description: Strings.tr(row.favorite ? "Remove favorite" : "Save favorite")
        onClicked: row.favoriteRequested()
    }
    Text {
        x: 8; y: 38; width: parent.width - 16
        text: row.station.tags || Strings.tr("No tags")
        textFormat: Text.PlainText
        elide: Text.ElideRight
        color: row.api.foreground
        opacity: 0.72
        font.family: row.api.fontFamily
        font.pixelSize: 11
    }
    Text {
        x: 8; y: 54; width: parent.width - 16
        text: (row.station.codec || Strings.tr("Unknown codec")) + (row.station.bitrate ? " · " + row.station.bitrate + " kb/s" : "")
        textFormat: Text.PlainText
        color: row.api.foreground
        opacity: 0.58
        font.family: row.api.fontFamily
        font.pixelSize: 11
    }
    Rectangle {
        visible: !row.last
        x: 8; width: parent.width - 16; height: 1
        anchors.bottom: parent.bottom
        color: row.api.foreground
        opacity: 0.12
    }
}
