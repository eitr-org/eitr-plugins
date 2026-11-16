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
    Canvas {
        id: glyph
        width: 20; height: 20
        anchors.centerIn: parent
        onPaint: {
            const context = getContext("2d");
            context.reset();
            context.strokeStyle = bar.api.foreground;
            context.lineWidth = 1.4;
            context.beginPath(); context.arc(10, 10, 8, 0, Math.PI * 2); context.stroke();
            context.beginPath(); context.ellipse(6, 2, 8, 16); context.stroke();
            context.beginPath(); context.moveTo(2, 10); context.lineTo(18, 10); context.stroke();
            if (bar.stationName) {
                context.fillStyle = bar.api.accent;
                context.beginPath(); context.arc(16.5, 16.5, 3, 0, Math.PI * 2); context.fill();
            }
        }
    }
    onStationNameChanged: glyph.requestPaint()
    Connections {
        target: bar.api
        function onThemeChanged() { glyph.requestPaint(); }
    }
    HoverHandler {
        id: hover
        onHoveredChanged: if (hovered) bar.api.runDataCommand()
    }
}
