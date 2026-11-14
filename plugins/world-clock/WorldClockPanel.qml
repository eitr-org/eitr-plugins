pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import Quickshell.Io
import "WorldClockState.js" as State

Item {
    id: panel
    required property var api
    readonly property var streamed: State.latest(api)
    property var savedStatus: null
    readonly property var status: savedStatus && (!streamed || savedStatus.updated > streamed.updated) ? savedStatus : State.merge(streamed, savedStatus)
    property string error: ""
    readonly property string runtime: decodeURIComponent(Qt.resolvedUrl("runtime.py").toString().replace(/^file:\/\//, ""))
    property var matches: []
    property alias searchText: search.text
    function runSearch() {
        if (finder.running) return;
        if (!search.text.trim()) { matches = []; return; }
        finder.command = ["python3", runtime, "search", search.text.trim()];
        finder.running = true;
    }
    Timer { id: debounce; interval: 180; onTriggered: panel.runSearch() }
    Process {
        id: finder
        stdout: StdioCollector { id: found }
        stderr: StdioCollector { id: searchFailure }
        onExited: function(exitCode) {
            if (exitCode !== 0) panel.error = searchFailure.text || "Search failed";
            else {
                try {
                    const result = JSON.parse(found.text);
                    if (result.query === search.text.trim()) panel.matches = result.matches;
                    else debounce.restart();
                } catch (error) { panel.error = "Could not read search results"; }
            }
        }
    }
    implicitWidth: 400
    implicitHeight: body.implicitHeight

    function save(settings) {
        if (writer.running) return;
        error = "";
        writer.command = ["python3", runtime, "save", JSON.stringify(settings)];
        writer.running = true;
    }
    function addCity(result) {
        if (!status || writer.running || status.cities.length >= 24
                || status.cities.some(city => city.zone === result.zone)) return;
        const settings = State.settings(status);
        const city = {zone: result.zone, label: result.label};
        if (result.country) { city.name = result.name; city.country = result.country; }
        settings.cities.push(city);
        save(settings);
    }
    function changeCity(index, action, label) {
        if (!status) return;
        const settings = State.settings(status);
        if (action === "label") settings.cities[index].label = label.trim();
        else if (action === "remove") settings.cities.splice(index, 1);
        else {
            const destination = index + (action === "up" ? -1 : 1);
            if (destination < 0 || destination >= settings.cities.length) return;
            const city = settings.cities.splice(index, 1)[0];
            settings.cities.splice(destination, 0, city);
        }
        save(settings);
    }
    Process {
        id: writer
        stdout: StdioCollector { id: saved }
        stderr: StdioCollector { id: failure }
        onExited: function(exitCode) {
            if (exitCode !== 0) panel.error = failure.text || "Could not save settings";
            else { panel.savedStatus = State.parse(saved.text); search.text = ""; }
        }
    }

    Column {
        id: body
        width: parent.width
        spacing: 12
        Text {
            text: "World clock"
            color: panel.api.foreground
            font.family: panel.api.fontFamily
            font.pixelSize: panel.api.headingSize
            font.bold: true
        }
        Text {
            width: parent.width
            text: panel.error || (panel.status ? panel.status.error || "" : "") || panel.api.dataError || (!panel.status ? "Loading…" :
                panel.status.cities.length ? "Edit labels; use arrows to change the order." : "Add a city to show its time beside the clock.")
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: panel.api.foreground
            opacity: 0.72
            font.family: panel.api.fontFamily
            font.pixelSize: panel.api.captionSize
        }
        Repeater {
            model: panel.status ? panel.status.cities : []
            Column {
                id: cityRow
                required property var modelData
                required property int index
                width: body.width
                spacing: 4
                Rectangle { width: parent.width; height: 1; color: Qt.alpha(panel.api.foreground, 0.12) }
                Row {
                    spacing: 6
                    Text {
                        text: cityRow.modelData.flag || ""
                        width: 24; height: 32; verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 18
                    }
                    TextField {
                        width: 92
                        text: cityRow.modelData.label
                        maximumLength: 12
                        color: panel.api.foreground
                        selectionColor: Qt.alpha(panel.api.accent, 0.35)
                        selectedTextColor: panel.api.foreground
                        Accessible.name: "Label for " + cityRow.modelData.zone
                        font.family: panel.api.fontFamily
                        font.pixelSize: panel.api.bodySize
                        selectByMouse: true
                        background: Rectangle { color: Qt.alpha(panel.api.foreground, 0.04); radius: panel.api.radius; border.color: Qt.alpha(panel.api.foreground, 0.15) }
                        onEditingFinished: if (text.trim() && text.trim() !== cityRow.modelData.label) panel.changeCity(cityRow.index, "label", text)
                    }
                    Text {
                        text: State.time(cityRow.modelData, panel.api.clockFormat)
                        width: 88; height: 32; verticalAlignment: Text.AlignVCenter
                        color: panel.api.foreground
                        font.family: panel.api.fontFamily
                        font.pixelSize: panel.api.bodySize
                    }
                    WorldClockButton { api: panel.api; glyph: "↑"; description: "Move up"; enabled: cityRow.index > 0 && !writer.running; onClicked: panel.changeCity(cityRow.index, "up", "") }
                    WorldClockButton { api: panel.api; glyph: "↓"; description: "Move down"; enabled: panel.status && cityRow.index < panel.status.cities.length - 1 && !writer.running; onClicked: panel.changeCity(cityRow.index, "down", "") }
                    WorldClockButton { api: panel.api; glyph: "×"; description: "Remove"; enabled: !writer.running; onClicked: panel.changeCity(cityRow.index, "remove", "") }
                }
                Text {
                    width: parent.width
                    text: (cityRow.modelData.name || cityRow.modelData.zone.replace(/_/g, " ")) + " · " + cityRow.modelData.day + " · " + cityRow.modelData.offset
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: panel.api.foreground
                    opacity: 0.72
                    font.family: panel.api.fontFamily
                    font.pixelSize: panel.api.captionSize
                }
            }
        }
        Row {
            spacing: 6
            Text { text: "Cities on the bar"; height: 32; verticalAlignment: Text.AlignVCenter; color: panel.api.foreground; font.family: panel.api.fontFamily; font.pixelSize: panel.api.bodySize }
            Repeater {
                model: [1, 2]
                WorldClockButton {
                    required property int modelData
                    api: panel.api
                    text: (panel.status && panel.status.barCount === modelData ? "✓ " : "") + modelData
                    enabled: panel.status !== null && !panel.status.error && !writer.running
                    onClicked: { const settings = State.settings(panel.status); settings.barCount = modelData; panel.save(settings); }
                }
            }
        }
        TextField {
            id: search
            width: parent.width
            enabled: panel.status !== null && !panel.status.error
            placeholderText: "Search city, state, country or time zone"
            onTextChanged: { panel.matches = []; debounce.restart(); }
            color: panel.api.foreground
            placeholderTextColor: Qt.alpha(panel.api.foreground, 0.72)
            selectionColor: Qt.alpha(panel.api.accent, 0.35)
            selectedTextColor: panel.api.foreground
            font.family: panel.api.fontFamily
            font.pixelSize: panel.api.bodySize
            selectByMouse: true
            maximumLength: 100
            background: Rectangle { color: Qt.alpha(panel.api.foreground, 0.04); radius: panel.api.radius; border.color: Qt.alpha(panel.api.foreground, 0.15) }
        }
        Repeater {
            model: panel.matches
            Rectangle {
                id: resultRow
                required property var modelData
                width: body.width; height: 48
                radius: panel.api.radius
                color: hover.containsMouse ? Qt.alpha(panel.api.foreground, 0.10) : "transparent"
                property bool selectable: panel.status && panel.status.cities.length < 24 && !writer.running
                    && !panel.status.cities.some(city => city.zone === modelData.zone)
                opacity: selectable ? 1 : 0.5
                activeFocusOnTab: selectable
                Accessible.role: Accessible.Button
                Accessible.name: modelData.name + ", " + modelData.state + ", " + modelData.countryName
                function choose() {
                    if (!selectable) return;
                    panel.addCity(modelData);
                }
                Keys.onReturnPressed: choose()
                Keys.onSpacePressed: choose()
                border.width: activeFocus ? 1 : 0
                border.color: panel.api.accent
                Text {
                    x: 4; width: 28; anchors.verticalCenter: parent.verticalCenter
                    text: resultRow.modelData.flag; font.pixelSize: 18
                }
                Column {
                    x: 38; width: parent.width - 42; anchors.verticalCenter: parent.verticalCenter
                    Text {
                        width: parent.width; elide: Text.ElideRight
                        text: resultRow.modelData.name; textFormat: Text.PlainText
                        color: panel.api.foreground; font.family: panel.api.fontFamily; font.pixelSize: panel.api.bodySize
                    }
                    Text {
                        width: parent.width; elide: Text.ElideRight
                        text: [resultRow.modelData.state, resultRow.modelData.countryName].filter(value => value).join(", ")
                        textFormat: Text.PlainText
                        color: panel.api.foreground; opacity: 0.72
                        font.family: panel.api.fontFamily; font.pixelSize: panel.api.captionSize
                    }
                }
                MouseArea {
                    id: hover; anchors.fill: parent; hoverEnabled: true
                    cursorShape: resultRow.selectable ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: resultRow.choose()
                }
            }
        }

        Text {
            visible: search.text.trim() !== "" && panel.matches.length === 0
            text: finder.running || debounce.running ? "Searching…" : "No matching cities or time zones"
            color: panel.api.foreground
            font.family: panel.api.fontFamily
            font.pixelSize: panel.api.captionSize
        }
    }
}
