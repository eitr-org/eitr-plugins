pragma ComponentBehavior: Bound
import QtQuick
import "Strings.js" as Strings

Item {
    id: bar
    required property var api
    property var playing: null
    readonly property string stationName: playing ? playing.station.name : ""
    implicitWidth: 24; implicitHeight: 24
    function update() {
        try { playing = JSON.parse(api.dataText).playing || null; }
        catch (error) { playing = null; }
        api.detail = stationName ? Strings.tr("Now playing") + " · " + stationName : "";
    }
    Component.onCompleted: update()
    Connections {
        target: bar.api
        function onDataTextChanged() { bar.update(); }
    }
    // The same 15 px glyph size as Eitr's own status icons.
    Text {
        anchors.centerIn: parent
        text: "\u{F01E7}"
        color: bar.api.foreground
        font.family: bar.api.fontFamily; font.pixelSize: 15
    }
    Rectangle {
        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 3
        width: 6; height: 6; radius: 3
        visible: bar.stationName !== ""
        color: bar.api.accent
    }
    HoverHandler {
        id: hover
        onHoveredChanged: if (hovered) bar.api.runDataCommand()
    }
}
