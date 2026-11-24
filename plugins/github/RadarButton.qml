import QtQuick

Item {
    id: host
    required property var api
    required property string label
    property string glyph: ""
    property bool selected: false
    property bool leftAligned: false
    property bool flat: false
    property bool spinning: false
    property int buttonSize: 28
    readonly property Item buttonItem: control.item
    signal clicked()

    implicitWidth: glyph ? buttonSize : Math.ceil(metrics.advanceWidth) + 20
    implicitHeight: glyph ? buttonSize : 32

    TextMetrics {
        id: metrics
        text: host.label
        font.family: host.api.fontFamily
        font.pixelSize: control.item ? control.item.textSize : host.api.bodySize
    }
    Loader {
        id: control
        anchors.fill: parent
        sourceComponent: host.api.controls.button
        onLoaded: {
            item.text = Qt.binding(() => host.glyph ? "" : host.label);
            item.textAlignment = host.leftAligned ? Text.AlignLeft : Text.AlignHCenter;
            item.flat = Qt.binding(() => host.glyph !== "" || host.flat);
            item.selected = Qt.binding(() => host.selected);
            host.buttonItem.Accessible.name = Qt.binding(() => host.label);
            item.clicked.connect(function() { host.clicked(); });
        }
    }
    RadarText {
        id: symbol
        api: host.api
        anchors.centerIn: parent
        text: host.glyph
        font.family: "JetBrainsMono Nerd Font"
        font.pixelSize: host.buttonSize - 10
    }
    RotationAnimator {
        target: symbol
        from: 0
        to: 360
        duration: 950
        loops: Animation.Infinite
        running: host.spinning && host.visible
        onRunningChanged: if (!running) symbol.rotation = 0
    }
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    RadarTooltip {
        api: host.api
        visible: host.glyph !== "" && hover.hovered
        text: host.label
    }
}
