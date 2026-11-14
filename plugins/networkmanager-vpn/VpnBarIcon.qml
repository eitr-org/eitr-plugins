import QtQuick
import "VpnState.js" as VpnState

// The bar slot: the VPN shield emblem at full strength while a profile is connected
// and dimmed while disconnected, on iwd or unavailable.
Item {
    id: icon
    required property var api
    readonly property var status: VpnState.parse(api.dataText)
    readonly property bool connected: status !== null && status.state === "connected"
    implicitWidth: 24
    implicitHeight: 24

    VpnLogo {
        anchors.centerIn: parent
        size: 18
        color: icon.api.foreground
        opacity: icon.connected ? 1 : 0.45
    }
}
