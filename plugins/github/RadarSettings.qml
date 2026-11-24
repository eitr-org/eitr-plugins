import QtQuick
import QtQuick.Layouts
import "Strings.js" as Strings

ColumnLayout {
    id: root
    required property var api
    required property var accounts
    required property var options
    signal save(string key, var value, string account)

    spacing: 9

    RadarSettingsHeading { api: root.api; text: Strings.tr("Accounts & owners") }
    RadarText {
        api: root.api; Layout.fillWidth: true; wrapMode: Text.Wrap
        text: Strings.tr("Separate names with commas. Leave empty to watch all owners.")
    }
    Repeater {
        model: root.accounts
        RadarSettingField {
            required property var modelData
            Layout.fillWidth: true
            api: root.api
            label: modelData.label + (modelData.login ? " · @" + modelData.login : "")
            value: ((root.options.owners || {})[modelData.id] || []).join(", ")
            onSave: value => root.save("owners", value, modelData.id)
        }
    }
    RadarSettingsHeading { api: root.api; text: Strings.tr("Rules") }
    Loader {
        Layout.fillWidth: true
        sourceComponent: root.api.controls.dropdown
        onLoaded: {
            item.floatingLabel = Strings.tr("Team review requests");
            item.helperText = Strings.tr("When team requests count as your move");
            item.choices = [{value: "until-reviewed", label: Strings.tr("Until I review")},
                {value: "always", label: Strings.tr("Always")}, {value: "never", label: Strings.tr("Never")}];
            item.current = Qt.binding(() => root.options.team_requests || "until-reviewed");
            item.chosen.connect(value => root.save("team_requests", value, ""));
        }
    }
    Repeater {
        model: [["ignore_teams", "Ignored teams (comma-separated)"], ["bots", "Bot logins (comma-separated)"]]
        RadarSettingField {
            required property var modelData
            Layout.fillWidth: true
            api: root.api; label: Strings.tr(modelData[1])
            value: (root.options[modelData[0]] || []).join(", ")
            onSave: value => root.save(modelData[0], value, "")
        }
    }
    Repeater {
        model: [
            ["ready", "Count approved PRs ready to merge"],
            ["failure", "Count failing CI on your PRs"],
            ["conflict", "Count conflicts on your PRs"],
            ["commits_after_feedback", "New commits after comments or changes requested"],
            ["commits_after_approval", "New commits after approval"],
            ["replies", "Replies in your review threads"],
            ["dismissed", "Dismissed reviews"],
            ["while_changes_requested", "Count requests while changes are open"],
            ["while_reviewing", "Count requests while someone is reviewing"]
        ]
        RowLayout {
            id: setting
            required property var modelData
            Layout.fillWidth: true
            RadarText {
                api: root.api; Layout.fillWidth: true; wrapMode: Text.Wrap
                text: Strings.tr(setting.modelData[1])
            }
            Loader {
                readonly property Item switchItem: item
                sourceComponent: root.api.controls.toggle
                onLoaded: {
                    switchItem.Accessible.name = Strings.tr(setting.modelData[1]);
                    item.checked = Qt.binding(() => !!root.options[setting.modelData[0]]);
                    item.toggled.connect(function() {
                        root.save(setting.modelData[0], item.checked, "");
                    });
                }
            }
        }
    }
    RadarSettingsHeading { api: root.api; text: Strings.tr("Notifications") }
    RowLayout {
        Layout.fillWidth: true
        RadarText {
            api: root.api
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: Strings.tr("Notify when a pull request needs you")
        }
        Loader {
            readonly property Item switchItem: item
            sourceComponent: root.api.controls.toggle
            onLoaded: {
                switchItem.Accessible.name = Strings.tr("Notify when a pull request needs you");
                item.checked = Qt.binding(() => root.options.notifications !== false);
                item.toggled.connect(function() { root.save("notifications", item.checked, ""); });
            }
        }
    }
}
