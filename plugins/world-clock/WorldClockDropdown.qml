import QtQuick
import QtQuick.Controls.Basic

ComboBox {
    id: control
    required property var api
    model: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    implicitWidth: 88
    implicitHeight: 32
    Accessible.name: "Cities on the bar"
    opacity: enabled ? 1 : 0.5
    contentItem: Text {
        leftPadding: 8; rightPadding: 28
        text: control.displayText
        color: control.api.foreground
        verticalAlignment: Text.AlignVCenter
        font.family: control.api.fontFamily
        font.pixelSize: control.api.bodySize
    }
    indicator: Text {
        x: control.width - width - 10
        anchors.verticalCenter: parent.verticalCenter
        text: "⌄"
        rotation: control.popup.visible ? 180 : 0
        color: control.api.foreground
    }
    background: Rectangle {
        radius: control.api.radius
        color: Qt.alpha(control.api.foreground, control.hovered ? 0.10 : 0.04)
        border.color: control.activeFocus ? control.api.accent : Qt.alpha(control.api.foreground, 0.15)
    }
    delegate: ItemDelegate {
        id: choice
        required property int index
        required property var modelData
        width: control.width - 8
        height: 32
        highlighted: control.highlightedIndex === index
        contentItem: Text {
            text: choice.modelData
            color: control.currentIndex === choice.index ? control.api.accent : control.api.foreground
            font.family: control.api.fontFamily
            font.pixelSize: control.api.bodySize
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: control.api.radius
            color: Qt.alpha(control.api.foreground, choice.highlighted || control.currentIndex === choice.index ? 0.10 : 0)
        }
    }
    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 4
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 264)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
        background: Rectangle {
            color: control.api.background
            radius: control.api.radius + 4
            border.color: Qt.alpha(control.api.foreground, 0.15)
        }
    }
}
