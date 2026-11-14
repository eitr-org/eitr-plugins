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
    signal copyRequested(string value)
    spacing: 6

    Repeater {
        model: [
            {label: Eitr.I18n.tr("Active tunnel"), value: details.status.activeTunnel || details.status.interface || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("Endpoint"), value: details.copiedText !== "" && details.copiedText === details.endpoint
                ? Eitr.I18n.tr("Copied") : details.endpoint || Eitr.I18n.tr("Unavailable"), copy: details.endpoint !== ""},
            {label: Eitr.I18n.tr("Transfer"), value: details.status.transfer || Eitr.I18n.tr("0 B received, 0 B sent"), copy: false},
            {label: Eitr.I18n.tr("Latest handshake"), value: details.status.handshake || Eitr.I18n.tr("Pending"), copy: false}
        ]
        Item {
            id: fact
            required property var modelData
            width: details.width
            height: Math.max(24, value.implicitHeight)
            Text {
                width: (parent.width - 12) * 0.4
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
                x: parent.width - width - (copyButton.visible ? copyButton.width + 6 : 0)
                width: (parent.width - 12) * 0.6 - (copyButton.visible ? copyButton.width + 6 : 0)
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignRight
                text: fact.modelData.value
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
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
