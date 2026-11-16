import QtQuick
import "PhoneState.js" as State
import "Strings.js" as Strings

Item {
    id: icon
    required property var api
    property var status: null
    readonly property var phone: State.connected(status)
    readonly property string detail: phone ? phone.name + (phone.battery === null ? "" : " · " + phone.battery + "%") : Strings.tr("No phone connected")
    implicitWidth: 24; implicitHeight: 24

    function update(line) {
        const parsed = State.parse(line);
        if (parsed !== null) status = parsed;
        api.detail = detail;
    }
    Component.onCompleted: update(api.streamLine || api.dataText || "")
    Connections {
        target: icon.api
        function onStreamReceived(line) { icon.update(line); }
        function onDataTextChanged() { icon.update(icon.api.dataText); }
    }
    Text {
        anchors.centerIn: parent
        text: "\u{F011C}"
        color: icon.api.foreground
        opacity: icon.phone ? 1 : 0.4
        font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 18
    }
}
