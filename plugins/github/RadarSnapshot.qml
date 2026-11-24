import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: reader
    property bool observing: true
    property var fixture: null
    property var loaded: ({accounts: [], count: 0, options: ({})})
    readonly property var value: fixture || loaded

    FileView {
        path: reader.observing && !reader.fixture
            ? (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state")
                + "/eitr/plugins/github/snapshot.json"
            : ""
        watchChanges: path !== ""
        printErrors: false
        onFileChanged: reload()
        onLoaded: {
            try { reader.loaded = Object.assign({accounts: [], count: 0, options: ({})}, JSON.parse(text())); }
            catch (error) { reader.loaded = ({accounts: [], count: 0, options: ({})}); }
        }
    }
}
