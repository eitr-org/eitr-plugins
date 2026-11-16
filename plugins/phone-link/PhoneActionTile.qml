import QtQuick
import QtQuick.Controls.Basic
import "Strings.js" as Strings

Item {
    id: tile
    required property var api
    required property string text
    required property string glyph
    property bool supported: true
    property bool busy: false
    readonly property string explanation: supported ? "" : Strings.tr("Not shared by this phone")
    signal clicked()
    implicitHeight: Math.max(76, content.implicitHeight + 20)
    height: implicitHeight

    Loader {
        anchors.fill: parent
        sourceComponent: tile.api.controls.button
        onLoaded: {
            item.text = "";
            item.available = Qt.binding(() => tile.supported && !tile.busy);
            item.Accessible.name = Qt.binding(() => tile.text);
            item.Accessible.description = Qt.binding(() => tile.explanation);
            item.clicked.connect(() => tile.clicked());
        }
    }
    Column {
        id: content
        width: parent.width - 12
        anchors.centerIn: parent
        spacing: 6
        opacity: tile.supported && !tile.busy ? 1 : 0.45
        PhoneLabel {
            api: tile.api; width: parent.width
            text: tile.glyph; font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 24
            horizontalAlignment: Text.AlignHCenter
        }
        PhoneLabel {
            api: tile.api; width: parent.width
            text: tile.text
            horizontalAlignment: Text.AlignHCenter
        }
    }
    HoverHandler { id: hover }
    ToolTip {
        visible: tile.explanation !== "" && hover.hovered
        delay: 500
        text: tile.explanation
        contentItem: PhoneLabel { api: tile.api; text: tile.explanation; font.pixelSize: tile.api.captionSize }
        background: Rectangle {
            color: tile.api.background; radius: tile.api.radius
            border.color: Qt.alpha(tile.api.foreground, 0.15)
        }
    }
}
