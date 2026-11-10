pragma ComponentBehavior: Bound
import QtQuick
import Eitr as Eitr

// This computer on the tailnet: label captions on the left, values on the right with
// tabular figures, and a copy action beside its first (IPv4) Tailscale address.
Column {
    id: details
    required property var api
    required property var status
    property string copiedAddress: ""
    readonly property string address: (status.addresses || [])[0] || ""
    signal copyRequested(string address)
    spacing: 6

    Repeater {
        model: [
            {label: Eitr.I18n.tr("Device"), value: details.status.device || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("Tailscale IP"), value: details.copiedAddress !== "" && details.copiedAddress === details.address
                ? Eitr.I18n.tr("Copied") : details.address || Eitr.I18n.tr("Unavailable"), copy: details.address !== ""},
            {label: Eitr.I18n.tr("Network"), value: details.status.network || Eitr.I18n.tr("Unavailable"), copy: false}
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
            TailscaleButton {
                id: copyButton
                api: details.api
                visible: fact.modelData.copy
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                glyph: "\u{F018F}"
                description: Eitr.I18n.tr("Copy address")
                onClicked: details.copyRequested(details.address)
            }
        }
    }
}
