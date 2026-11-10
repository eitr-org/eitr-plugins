import QtQuick
import "TailscaleState.js" as TailscaleState

// The bar slot: Tailscale's logo in the bar's colour, at full strength while connected
// and dimmed while off, signed out or unavailable.
Item {
    id: icon
    required property var api
    readonly property var status: TailscaleState.parse(api.dataText)
    readonly property bool connected: status !== null && status.state === "connected"
    implicitWidth: 24
    implicitHeight: 24

    TailscaleLogo {
        anchors.centerIn: parent
        // Tailscale's logo stays black or white, never tinted: white on dark bars, black on light.
        color: icon.api.foreground.hslLightness > 0.5 ? "#ffffff" : "#000000"
        opacity: icon.connected ? 1 : 0.45
    }
}
