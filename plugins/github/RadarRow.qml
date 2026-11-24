import QtQuick
import QtQuick.Layouts
import "RadarPresentation.js" as Presentation
import "Strings.js" as Strings

Rectangle {
    id: root
    required property var api
    property bool showRepo: true
    required property var pr
    required property var account
    required property real now
    readonly property bool highlighted: hover.hovered || activeFocus
    readonly property var ci: Presentation.ciState(pr.ci)
    readonly property var reviewers: Presentation.reviewers(pr)
    readonly property var reviewStatus: Presentation.reviewStatus(pr)
    readonly property var reasons: Presentation.reasons(pr)
    signal openRequested()

    implicitHeight: 46
    radius: Math.min(api.radius, 4)
    color: Qt.alpha(api.foreground, highlighted ? 0.10 : 0.04)
    border.color: Qt.alpha(api.foreground, activeFocus ? 0.48 : 0.15)

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: pr.title
    Accessible.description: [account.label, pr.repo + " #" + pr.number, pr.author].concat(reasons).join(" · ")
    Accessible.onPressAction: root.openRequested()
    Keys.onReturnPressed: root.openRequested()
    Keys.onSpacePressed: root.openRequested()
    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.openRequested() }

    // Review state leads the row (it decides what happens next); CI's status light ends it.
    RadarText {
        api: root.api
        objectName: "reviewStatus"
        x: 10
        visible: !!root.reviewStatus
        anchors.verticalCenter: parent.verticalCenter
        font.pixelSize: 15
        font.family: "JetBrainsMono Nerd Font"
        text: root.reviewStatus ? root.reviewStatus.glyph : ""
        color: Presentation.tone(api, root.reviewStatus ? root.reviewStatus.key : "")
        opacity: root.pr.draft || !(root.reviewStatus && root.reviewStatus.key) ? 0.65 : 1
        HoverHandler { id: statusHover }
        RadarTooltip {
            api: root.api
            visible: statusHover.hovered && !!root.reviewStatus
            text: root.reviewStatus ? Strings.tr(root.reviewStatus.label) : ""
        }
    }

    RadarText {
        api: root.api
        objectName: "ciStatus"
        anchors.right: parent.right
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        font.pixelSize: 12
        font.family: "JetBrainsMono Nerd Font"
        text: root.ci.glyph
        color: Presentation.tone(api, root.ci.key)
        opacity: root.pr.draft || !root.ci.key ? 0.65 : 1
        HoverHandler { id: ciHover }
        RadarTooltip {
            api: root.api
            visible: ciHover.hovered
            text: Strings.tr("CI") + " · " + Strings.tr(root.pr.ci)
        }
    }

    ColumnLayout {
        anchors.left: parent.left
        anchors.leftMargin: 36
        anchors.right: parent.right
        anchors.rightMargin: 36
        anchors.verticalCenter: parent.verticalCenter
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            RadarText {
                id: title
                api: root.api
                Layout.fillWidth: true
                text: root.pr.title
                font.pixelSize: api.bodySize + 1
                font.bold: !root.pr.draft
                opacity: root.pr.draft ? 0.72 : 1
                elide: Text.ElideRight
                HoverHandler { id: titleHover }
                RadarTooltip {
                    api: root.api
                    visible: titleHover.hovered && title.truncated
                    text: root.pr.title
                }
            }
            RadarText {
                api: root.api
                text: Presentation.age(Date.parse(root.pr.updated), root.now)
                font.pixelSize: api.captionSize
                opacity: 0.72
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 5
            opacity: root.pr.draft ? 0.72 : 1
            Item {
                id: reference
                Layout.preferredWidth: root.showRepo ? Math.min(repoWidth.advanceWidth + prNumber.implicitWidth, root.width * 0.25) : prNumber.implicitWidth
                Layout.preferredHeight: prNumber.implicitHeight
                opacity: 0.72
                RadarText {
                    id: repoName
                    api: root.api
                    visible: root.showRepo
                    width: root.showRepo ? Math.max(0, reference.width - prNumber.implicitWidth) : 0
                    text: root.pr.repo
                    elide: Text.ElideMiddle
                    font.pixelSize: api.captionSize - 1
                }
                TextMetrics { id: repoWidth; font: repoName.font; text: repoName.text }
                RadarText {
                    id: prNumber
                    api: root.api
                    anchors.left: repoName.right
                    text: (root.showRepo ? " #" : "#") + root.pr.number
                    font.pixelSize: api.captionSize - 1
                }
                HoverHandler { id: referenceHover }
                RadarTooltip {
                    api: root.api
                    visible: referenceHover.hovered && repoName.truncated
                    text: root.pr.repo + prNumber.text
                }
            }
            RadarText {
                api: root.api
                Layout.maximumWidth: root.width * 0.15
                text: "@" + root.pr.author
                elide: Text.ElideRight
                font.pixelSize: api.captionSize - 1
                opacity: 0.72
            }
            Item {
                id: reasonSpace
                Layout.fillWidth: true
                Layout.preferredHeight: 16
                clip: true
                Flow {
                    width: reasonSpace.width
                    spacing: 4
                    Repeater {
                        model: root.reasons
                        RadarChip {
                            required property string modelData
                            api: root.api
                            label: modelData
                            maxWidth: Math.min(220, reasonSpace.width)
                        }
                    }
                }
                HoverHandler { id: reasonHover }
                RadarTooltip {
                    api: root.api
                    visible: reasonHover.hovered && root.reasons.length > 0
                    text: root.reasons.join(" · ")
                }
            }
            Row {
                visible: root.reviewers.length > 0
                spacing: 3
                Repeater {
                    model: root.reviewers.slice(0, 3)
                    Rectangle {
                        required property var modelData
                        readonly property string stateColor: modelData.state === "APPROVED" ? "color2"
                            : modelData.state === "CHANGES_REQUESTED" ? "color1"
                            : modelData.state === "COMMENTED" ? "" : "color3"
                        width: 15; height: 15; radius: 7.5
                        color: Qt.alpha(Presentation.tone(root.api, stateColor), 0.16)
                        RadarText {
                            api: root.api
                            anchors.centerIn: parent
                            font.pixelSize: 10
                            font.bold: true
                            color: Presentation.tone(api, parent.stateColor)
                            text: parent.modelData.login.charAt(0).toUpperCase()
                        }
                    }
                }
                RadarText {
                    api: root.api
                    visible: root.reviewers.length > 3
                    font.pixelSize: 10
                    text: "+" + (root.reviewers.length - 3)
                }
                HoverHandler { id: reviewHover }
                RadarTooltip {
                    api: root.api
                    visible: reviewHover.hovered
                    text: root.reviewers.map(reviewer => reviewer.login + " · " + Strings.tr(reviewer.state)).join("\n")
                }
            }
        }
    }
}
