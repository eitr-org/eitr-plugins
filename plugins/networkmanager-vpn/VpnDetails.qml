pragma ComponentBehavior: Bound
import QtQuick
import Eitr as Eitr

// Active NetworkManager VPN profile details: protocol, interface, address (with copy),
// server/gateway and DNS.
Column {
    id: details
    required property var api
    required property var status
    property string copiedAddress: ""
    readonly property string address: status.address || ""
    signal copyRequested(string value)
    spacing: 6

    Repeater {
        model: [
            {label: Eitr.I18n.tr("Active profile"), value: details.status.activeProfile || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("Protocol"), value: details.status.protocol || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("Interface"), value: details.status.interface || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("Address"), value: details.copiedAddress !== "" && details.copiedAddress === details.address
                ? Eitr.I18n.tr("Copied") : details.address || Eitr.I18n.tr("Unavailable"), copy: details.address !== ""},
            {label: Eitr.I18n.tr("Gateway"), value: details.status.endpoint || details.status.gateway || Eitr.I18n.tr("Unavailable"), copy: false},
            {label: Eitr.I18n.tr("DNS"), value: details.status.dns || Eitr.I18n.tr("Default"), copy: false}
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
            VpnButton {
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
