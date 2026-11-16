pragma ComponentBehavior: Bound
import QtQuick
import Quickshell.Io
import "Strings.js" as Strings

Item {
    id: backend
    objectName: "radio-backend"
    required property var api
    property var countries: []
    property var stations: []
    property var favorites: []
    property var playing: null
    property int volume: 60
    property bool stale: false
    property bool more: false
    property string error: ""
    property bool countriesFailed: false
    property bool stationsFailed: false
    readonly property bool loadFailed: countriesFailed || stationsFailed
    property string queryMode: "country"
    property string queryValue: ""
    property int offset: 0
    property string wanted: ""
    readonly property bool busy: finder.running || countryReader.running || writer.running
    readonly property string script: decodeURIComponent(Qt.resolvedUrl("runtime.py").toString().replace(/^file:\/\//, ""))
    width: 0; height: 0

    function parse(payload) {
        try {
            const result = JSON.parse(payload);
            if (!result.ok) { error = Strings.tr(result.error || "Request failed"); return null; }
            return result;
        } catch (exception) { error = Strings.tr("Could not read radio data"); return null; }
    }
    function applyState(result) {
        if (!result) return;
        favorites = result.favorites || [];
        playing = result.playing || null;
        volume = result.volume === undefined ? volume : result.volume;
    }
    function activate() {
        if (!api.observed) {
            finder.running = false; countryReader.running = false; reader.running = false;
            return;
        }
        refresh();
        if (countries.length === 0) loadCountries();
        if (wanted && stations.length === 0) begin();
    }
    function loadCountries() {
        if (!api.observed || countryReader.running) return;
        error = "";
        countriesFailed = false;
        countryReader.running = true;
    }
    function refresh() { if (api.observed && !reader.running && !writer.running) reader.running = true; }
    function search(mode, value, page) {
        queryMode = mode; queryValue = value; offset = page || 0;
        wanted = JSON.stringify([mode, value, offset]);
        stations = []; more = false; error = "";
        stationsFailed = false;
        begin();
    }
    function begin() {
        if (!api.observed || finder.running || !queryValue || !wanted) return;
        finder.key = wanted;
        finder.command = ["python3", script, "stations", queryMode, queryValue, String(offset)];
        finder.running = true;
    }
    function action(command, value) {
        if (writer.running) return;
        error = "";
        writer.payload = command === "play" || command === "favorite" ? JSON.stringify(value) : "";
        writer.command = ["python3", script, command].concat(command === "volume" ? [String(value)] : []);
        writer.stdinEnabled = true;
        writer.running = true;
    }
    function isFavorite(station) { return favorites.some(entry => entry.stationuuid === station.stationuuid); }
    Component.onCompleted: activate()
    Connections {
        target: backend.api
        function onObservedChanged() { backend.activate(); }
    }
    Timer { interval: 3000; repeat: true; running: backend.api.observed; onTriggered: backend.refresh() }
    Process {
        id: reader
        command: ["python3", backend.script, "state"]
        stdout: StdioCollector { id: stateOutput }
        onExited: exitCode => {
            if (backend.api.observed && !writer.running) backend.applyState(backend.parse(stateOutput.text));
        }
    }
    Process {
        id: countryReader
        command: ["python3", backend.script, "countries"]
        stdout: StdioCollector { id: countryOutput }
        onExited: exitCode => {
            if (!backend.api.observed) return;
            const result = backend.parse(countryOutput.text);
            backend.countriesFailed = !result || result.stale === true;
            if (result) { backend.countries = result.countries; backend.stale = result.stale; }
        }
    }
    Process {
        id: finder
        property string key: ""
        stdout: StdioCollector { id: searchOutput }
        onExited: exitCode => {
            if (!backend.api.observed) return;
            if (key !== backend.wanted) { backend.begin(); return; }
            const result = backend.parse(searchOutput.text);
            backend.stationsFailed = !result;
            if (result) { backend.stations = result.stations; backend.more = result.more; }
        }
    }
    Process {
        id: writer
        property string payload: ""
        onStarted: { write(payload); stdinEnabled = false; }
        stdout: StdioCollector { id: writeOutput }
        onExited: exitCode => { backend.applyState(backend.parse(writeOutput.text)); }
    }
}
