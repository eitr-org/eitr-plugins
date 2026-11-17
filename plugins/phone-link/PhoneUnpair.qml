import QtQuick
import "Strings.js" as Strings

Column {
    id: unpair
    required property var api
    property bool busy: false
    property bool confirming: false
    signal confirmed()
    spacing: 6

    PhoneButton {
        objectName: "unpair"
        api: unpair.api; flat: true
        visible: !unpair.confirming
        text: Strings.tr("Unpair"); available: !unpair.busy
        opacity: 0.72
        onClicked: unpair.confirming = true
    }
    Column {
        width: parent.width; spacing: 6
        visible: unpair.confirming
        PhoneLabel {
            api: unpair.api; width: parent.width
            text: Strings.tr("Unpair this device? You will need to pair it again to reconnect.")
            font.pixelSize: unpair.api.captionSize
        }
        Flow {
            width: parent.width; spacing: 6
            PhoneButton {
                objectName: "confirm-unpair"
                api: unpair.api; text: Strings.tr("Confirm unpair"); available: !unpair.busy
                onClicked: { unpair.confirmed(); unpair.confirming = false; }
            }
            PhoneButton {
                objectName: "cancel-unpair"
                api: unpair.api; text: Strings.tr("Cancel"); flat: true
                onClicked: unpair.confirming = false
            }
        }
    }
}
