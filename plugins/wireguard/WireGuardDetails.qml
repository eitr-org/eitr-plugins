pragma ComponentBehavior: Bound
import QtQuick
import Eitr as Eitr

// Active WireGuard tunnel details: endpoint, transfer and latest handshake with
// tabular figures, plus a copy action beside the endpoint address.
Column {
    id: details
    required property var api
    required property var status
    property string copiedText: ""
    readonly property string endpoint: status.endpoint || ""
    // Every value ends at the same edge, leaving a column for the copy buttons.
    readonly property real copyColumn: 34
    signal copyRequested(string value)
    // "6.60 KiB received, 6.87 KiB sent" (wg show's wording) as "↓ 6.60 KiB · ↑ 6.87 KiB", which fits one line.
    function arrows(transfer) {
        const parts = /^(.+) received, (.+) sent$/.exec(transfer || "");
        return parts ? "\u2193 " + parts[1] + " \u00B7 \u2191 " + parts[2] : (transfer || "");
    }
    spacing: 6

    Repeater {
        model: [
            {label: Eitr.I18n.tr("Active tunnel"), value: details.status.activeTunnel || details.status.interface || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("Endpoint"), value: details.copiedText !== "" && details.copiedText === details.endpoint
                ? Eitr.I18n.tr("Copied") : details.endpoint || Eitr.I18n.tr("Unavailable"), copy: details.endpoint !== ""},
            {label: Eitr.I18n.tr("Transfer"), value: details.arrows(details.status.transfer) || Eitr.I18n.tr("Unavailable"), copy: false},
            // Only `wg show` with administrator rights knows the handshake: without it, no row.
            {label: Eitr.I18n.tr("Latest handshake"), value: details.status.handshake || "", copy: false}
        ].filter(fact => fact.value !== "")
        Item {
            id: fact
            required property var modelData
            width: details.width
            height: Math.max(24, value.implicitHeight)
            Text {
                width: (parent.width - 12) * 0.32
                anchors.verticalCenter: parent.verticalCenter
                text: fact.modelData.label
                textFormat: Text.PlainText
                color: details.api.foreground
                opacity: 0.72
                font.family: details.api.fontFamily
                font.pixelSize: details.api.captionSize
            }
            Text {
                id: value
                x: parent.width - width - details.copyColumn
                width: (parent.width - 12) * 0.68 - details.copyColumn
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text: fact.modelData.value
                textFormat: Text.PlainText
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                color: details.api.foreground
                font.family: details.api.fontFamily
                font.pixelSize: details.api.captionSize
                font.features: {"tnum": 1}
            }
            WireGuardButton {
                id: copyButton
                api: details.api
                visible: fact.modelData.copy
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                glyph: "\u{F018F}"
                description: Eitr.I18n.tr("Copy endpoint")
                onClicked: details.copyRequested(details.endpoint)
            }
        }
    }
}
