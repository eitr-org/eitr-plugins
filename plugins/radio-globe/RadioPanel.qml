pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls.Basic
import Quickshell.Io
import Eitr as Eitr
import "Strings.js" as Strings

Item {
    id: panel
    required property var api
    property bool favoritesOnly: false
    property bool showGlobe: true
    property string searchText: ""
    property string searchMode: "name"
    property string countryCode: ""
    property string countryName: ""
    property bool reduceMotion: true
    readonly property var displayed: favoritesOnly ? backend.favorites.filter(station =>
        !searchText.trim() || (searchMode === "tag" ? station.tags : station.name).toLowerCase().indexOf(searchText.trim().toLowerCase()) !== -1) : backend.stations
    implicitWidth: 600
    implicitHeight: body.implicitHeight
    RadioBackend { id: backend; api: panel.api }
    FileView {
        path: panel.api.observed ? Eitr.Paths.config("quickshell/desktop-bar/bar-settings.json") : ""
        printErrors: false
        watchChanges: panel.api.observed
        onFileChanged: reload()
        onLoaded: {
            try { panel.reduceMotion = JSON.parse(text()).reduceMotion === "yes"; }
            catch (error) { panel.reduceMotion = true; }
        }
        onLoadFailed: panel.reduceMotion = true
    }
    function chooseCountry(country) {
        countryCode = country.code; countryName = country.name;
        globe.faceCountry(country);
        favoritesOnly = false;
        searchText = "";
        if (search.item) search.item.text = "";
        debounce.stop();
        backend.search("country", country.code, 0);
    }
    function runSearch() {
        if (favoritesOnly) return;
        if (searchText.trim()) backend.search(searchMode, searchText.trim(), 0);
        else if (countryCode) backend.search("country", countryCode, 0);
        else { backend.wanted = ""; backend.stations = []; }
    }
    Timer { id: debounce; interval: 400; running: false; onTriggered: if (panel.api.observed) panel.runSearch() }
    Column {
        id: body
        width: parent.width
        spacing: 8
        Row {
            width: parent.width; spacing: 6
            Text {
                width: parent.width - 150 - (retry.visible ? retry.width + 6 : 0); height: 32
                verticalAlignment: Text.AlignVCenter
                text: Strings.tr("Radio Globe")
                color: panel.api.foreground
                font.family: panel.api.fontFamily
                font.pixelSize: 16; font.bold: true
            }
            RadioAction {
                api: panel.api; width: 110
                text: Strings.tr("Favourites"); selected: panel.favoritesOnly
                onClicked: { panel.favoritesOnly = !panel.favoritesOnly; if (!panel.favoritesOnly) panel.runSearch(); }
            }
            RadioAction {
                objectName: "globe-toggle"
                api: panel.api; width: 28; icon: true; text: "◎"
                description: Strings.tr(panel.showGlobe ? "Hide globe" : "Show globe")
                selected: panel.showGlobe
                onClicked: panel.showGlobe = !panel.showGlobe
            }
            RadioAction {
                id: retry
                objectName: "retry"
                api: panel.api; width: 76
                text: Strings.tr("Retry")
                visible: backend.loadFailed
                enabled: !backend.busy
                onClicked: { backend.loadCountries(); backend.refresh(); panel.runSearch(); }
            }
        }
        Row {
            width: parent.width
            spacing: 6
            Loader {
                id: search
                width: parent.width - modeButton.width - 6; height: 32
                sourceComponent: panel.api.controls.textField
                onLoaded: {
                    item.placeholderText = Strings.tr("Search stations");
                    item.maximumLength = 100;
                    item.textChanged.connect(() => { panel.searchText = item.text; debounce.restart(); });
                    item.accepted.connect(() => { debounce.stop(); panel.runSearch(); });
                }
            }
            RadioAction {
                id: modeButton
                api: panel.api; width: 82
                text: Strings.tr(panel.searchMode === "name" ? "By name" : "By tag")
                onClicked: { panel.searchMode = panel.searchMode === "name" ? "tag" : "name"; debounce.restart(); }
            }
        }
        Row {
            id: explorer
            width: parent.width; height: Math.max(340, stationColumn.implicitHeight)
            spacing: panel.showGlobe ? 12 : 0
            RadioGlobe {
                id: globe
                api: panel.api
                width: panel.showGlobe ? Math.floor(explorer.width * 0.5) : 0
                height: explorer.height
                visible: panel.showGlobe
                countries: backend.countries
                reduceMotion: panel.reduceMotion
                onChosen: country => panel.chooseCountry(country)
            }
            Column {
                id: stationColumn
                width: panel.showGlobe ? explorer.width - Math.floor(explorer.width * 0.5) - 12 : explorer.width
                spacing: 4
                Loader {
                    width: parent.width
                    sourceComponent: panel.api.controls.dropdown
                    onLoaded: {
                        item.floatingLabel = Strings.tr("Country");
                        item.helperText = Strings.tr("Choose a dot or a country");
                        item.choices = Qt.binding(() => backend.countries.map(country => ({value: country.code, label: country.name + " · " + country.count})));
                        item.current = Qt.binding(() => panel.countryCode);
                        item.chosen.connect(value => {
                            const country = backend.countries.find(entry => entry.code === value);
                            if (country) panel.chooseCountry(country);
                        });
                    }
                }
                Text {
                    id: status
                    width: parent.width
                    text: backend.error ? Strings.tr("Request failed") : backend.stale ? Strings.tr("Offline · showing saved countries") : backend.busy ? Strings.tr("Loading…") : panel.favoritesOnly ? Strings.tr("Favourites") : panel.searchText.trim() ? Strings.tr("Search results") : panel.countryName || Strings.tr("Choose a country or search")
                    textFormat: Text.PlainText
                    elide: Text.ElideRight
                    color: panel.api.foreground
                    opacity: 0.78
                    font.family: panel.api.fontFamily
                    font.pixelSize: 12
                    Accessible.role: Accessible.AlertMessage
                }
                ListView {
                    id: list
                    width: parent.width
                    height: 236
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: panel.displayed
                    ScrollBar.vertical: ScrollBar {}
                    delegate: StationRow {
                        required property var modelData
                        width: list.width - 8
                        api: panel.api; station: modelData
                        favorite: backend.isFavorite(modelData)
                        playing: backend.playing !== null && backend.playing.station.stationuuid === modelData.stationuuid
                        enabled: !backend.busy
                        onPlayRequested: backend.action("play", modelData)
                        onFavoriteRequested: backend.action("favorite", modelData)
                    }
                    Text {
                        anchors.centerIn: parent
                        width: parent.width
                        visible: panel.displayed.length === 0 && !backend.busy
                        text: Strings.tr(panel.favoritesOnly ? "No saved favourites yet" : "No stations to show")
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        horizontalAlignment: Text.AlignHCenter
                        color: panel.api.foreground
                        opacity: 0.6
                        font.family: panel.api.fontFamily
                        font.pixelSize: 13
                    }
                }
            }
        }
        Text {
            width: parent.width
            visible: backend.error !== "" || backend.stale
            text: backend.error || Strings.tr("Offline · showing saved countries")
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: panel.api.foreground
            opacity: 0.78
            font.family: panel.api.fontFamily
            font.pixelSize: 12
        }
        Row {
            visible: !panel.favoritesOnly && (backend.more || backend.offset > 0)
            height: visible ? 32 : 0
            spacing: 6
            RadioAction {
                api: panel.api; text: Strings.tr("Previous")
                enabled: !backend.busy && backend.offset > 0
                onClicked: backend.search(backend.queryMode, backend.queryValue, Math.max(0, backend.offset - 50))
            }
            RadioAction {
                api: panel.api; text: Strings.tr("Next")
                enabled: !backend.busy && backend.more
                onClicked: backend.search(backend.queryMode, backend.queryValue, backend.offset + 50)
            }
        }
        NowPlaying { width: parent.width; api: panel.api; backend: backend }
        Text {
            width: parent.width
            text: Strings.tr("Station lists: Radio Browser. Streams: each station.")
            textFormat: Text.PlainText
            wrapMode: Text.Wrap
            color: panel.api.foreground
            opacity: 0.58
            font.family: panel.api.fontFamily
            font.pixelSize: 11
        }
    }
}
