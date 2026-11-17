pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import "NotesColors.js" as NotesColors

Item {
    id: root
    required property var api
    implicitWidth: 260
    implicitHeight: 240

    property bool persistData: true
    property string noteColor: "yellow"
    property bool loaded: false
    property bool dirty: false
    property bool applyingSaved: false

    readonly property bool lightTheme: api.foreground.hslLightness < 0.5
    readonly property bool themeMode: noteColor === "theme"
    readonly property var softColors: NotesColors.softPalette(noteColor, lightTheme)
    readonly property color fallbackThemePaper: api.palette && api.palette.surface
        ? api.palette.surface
        : Qt.rgba(api.background.r, api.background.g, api.background.b, Math.max(0.94, api.background.a))
    readonly property color paperColor: themeMode
        ? (api.surface === "panel" ? "transparent" : fallbackThemePaper)
        : softColors.paper
    readonly property color headerColor: themeMode ? Qt.alpha(api.foreground, 0.07) : softColors.header
    readonly property color borderColor: themeMode
        ? (editor.activeFocus ? api.accent : Qt.alpha(api.foreground, 0.16))
        : (editor.activeFocus ? api.accent : softColors.border)
    readonly property color inkColor: themeMode ? api.foreground : softColors.ink
    readonly property color placeholderColor: themeMode ? Qt.alpha(api.foreground, 0.55) : softColors.placeholder
    readonly property color swatchColor: themeMode ? api.accent : softColors.swatch

    function updateMenu() {
        if (typeof api.setMenu !== "function") return;
        const entries = NotesColors.COLORS.map(choice => ({
            id: choice.id,
            text: choice.label,
            checked: root.noteColor === choice.id,
            group: "Color"
        }));
        entries.push({id: "theme", text: "Theme", checked: root.noteColor === "theme", group: "Color"});
        api.setMenu(entries);
    }

    function applySaved(data) {
        applyingSaved = true;
        if (data && typeof data === "object") {
            noteColor = NotesColors.normalizeColor(data.color);
            editor.text = typeof data.text === "string" ? data.text : "";
        }
        applyingSaved = false;
        dirty = false;
        loaded = true;
        updateMenu();
    }

    function flushSave() {
        saveTimer.stop();
        if (!loaded || !persistData) return;
        dirty = false;
        if (typeof api.saveInstanceData === "function")
            api.saveInstanceData({version: 1, text: editor.text, color: noteColor});
    }

    onNoteColorChanged: {
        updateMenu();
        if (loaded && !applyingSaved) {
            dirty = true;
            flushSave();
        }
    }

    Component.onCompleted: {
        if ("acceptsKeyboard" in api) api.acceptsKeyboard = true;
        updateMenu();
        if (!persistData || api.instanceDataReady || !("instanceDataReady" in api))
            applySaved(api.instanceData);
    }

    Component.onDestruction: {
        if (dirty) flushSave();
    }

    Connections {
        target: root.api
        ignoreUnknownSignals: true
        function onInstanceDataLoaded() {
            if (!root.dirty) root.applySaved(root.api.instanceData);
        }
        function onKeyboardReleased() {
            editor.focus = false;
        }
        function onMenuTriggered(id) {
            if (id === "theme" || NotesColors.COLORS.some(choice => choice.id === id))
                root.noteColor = id;
        }
    }

    Timer {
        id: saveTimer
        interval: 350
        onTriggered: root.flushSave()
    }

    Rectangle {
        id: card
        anchors.fill: parent
        radius: root.api.radius
        color: root.paperColor

        // Top sticky-note header strip; dragging/resizing uses the host's Edit position action.
        Rectangle {
            id: header
            width: parent.width
            height: 26
            topLeftRadius: card.radius
            topRightRadius: card.radius
            bottomLeftRadius: 0
            bottomRightRadius: 0
            color: root.headerColor

            Text {
                id: noteIcon
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                text: "󰎞"
                color: root.inkColor
                opacity: 0.72
                font.family: root.api.fontFamily
                font.pixelSize: 13
            }

            Text {
                x: noteIcon.x + noteIcon.width + 6
                anchors.verticalCenter: parent.verticalCenter
                width: swatch.x - x - 8
                text: "Note"
                textFormat: Text.PlainText
                elide: Text.ElideRight
                color: root.inkColor
                opacity: 0.72
                font.family: root.api.fontFamily
                font.pixelSize: root.api.captionSize
            }

            Rectangle {
                id: swatch
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 8
                height: 8
                radius: 4
                color: root.swatchColor
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: root.borderColor
                opacity: 0.6
            }
        }

        ScrollView {
            id: scroll
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 10
            anchors.topMargin: 8
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            TextArea {
                id: editor
                width: scroll.availableWidth
                textFormat: TextEdit.PlainText
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                background: null
                padding: 0
                color: root.inkColor
                placeholderText: "Write a note"
                placeholderTextColor: root.placeholderColor
                selectionColor: Qt.alpha(root.swatchColor, 0.32)
                selectedTextColor: root.inkColor
                font.family: root.api.fontFamily
                font.pixelSize: root.api.bodySize
                Accessible.name: "Note"

                onTextChanged: {
                    if (root.loaded && !root.applyingSaved) {
                        root.dirty = true;
                        saveTimer.restart();
                    }
                }

                onActiveFocusChanged: {
                    if ("keyboardFocus" in root.api) root.api.keyboardFocus = activeFocus;
                    if (!activeFocus && root.dirty) root.flushSave();
                }

                Keys.onEscapePressed: function(event) {
                    editor.focus = false;
                    if (typeof root.api.releaseKeyboard === "function") root.api.releaseKeyboard();
                    event.accepted = true;
                }
            }

            MouseArea {
                anchors.fill: parent
                z: -1
                cursorShape: Qt.IBeamCursor
                onPressed: {
                    editor.forceActiveFocus();
                    editor.cursorPosition = editor.length;
                    if ("keyboardFocus" in root.api) root.api.keyboardFocus = true;
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            radius: card.radius
            color: "transparent"
            border.width: 1
            border.color: root.borderColor
            z: 2
        }
    }
}
