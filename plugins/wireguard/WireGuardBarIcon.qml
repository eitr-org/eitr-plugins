import QtQuick
import "WireGuardState.js" as WireGuardState

// The bar slot: WireGuard's official logo at full strength while a tunnel is active
// and dimmed while disconnected or unavailable.
Item {
    id: icon
    required property var api
    readonly property var status: WireGuardState.parse(api.dataText)
    readonly property bool connected: status !== null && status.state === "connected"
    implicitWidth: 24
    implicitHeight: 24

    WireGuardLogo {
        anchors.centerIn: parent
        size: 18
        background: icon.api.background
        dimmed: !icon.connected
    }
}
