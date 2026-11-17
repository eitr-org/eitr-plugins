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
    property string searchText: ""
    property string searchMode: "name"
    property string countryCode: ""
    property string countryName: ""
    property bool filterOpen: false
    // Leaves Favourites for the list it replaced.
    function closeFavorites() {
        if (!favoritesOnly) return;
        favoritesOnly = false;
        runSearch();
    }
    function chooseMode(mode) {
        filterOpen = false;
        if (mode === searchMode) return;
        searchMode = mode;
        debounce.restart();
        if (search.item) search.item.forceActiveFocus();
    }
    Keys.onEscapePressed: event => {
        if (filterOpen) filterOpen = false;
        else if (favoritesOnly) closeFavorites();
        else { event.accepted = false; return; }
        event.accepted = true;
    }
    property bool reduceMotion: true
    // By country, typing lists the matching countries; choosing one shows its stations.
    readonly property bool pickingCountry: searchMode === "country" && searchText.trim() !== "" && !favoritesOnly
    readonly property var countryMatches: pickingCountry ? backend.countries.filter(country =>
        country.name.toLowerCase().indexOf(searchText.trim().toLowerCase()) !== -1) : []
    readonly property var displayed: favoritesOnly ? backend.favorites.filter(station =>
        !searchText.trim() || (searchMode === "tag" ? station.tags : station.name).toLowerCase().indexOf(searchText.trim().toLowerCase()) !== -1) : backend.stations
    implicitWidth: 720
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
    // Turns the globe to a station as it starts: its own place, else its country's dot.
    function faceStation(station) {
        if (station.location) globe.facePlace(station.location[0], station.location[1]);
        else globe.faceCountry(backend.countries.find(country => country.code === station.countrycode));
    }
    function runSearch() {
        if (favoritesOnly || searchMode === "country") return;
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
                width: parent.width - (retry.visible ? retry.width + 6 : 0); height: 32
                verticalAlignment: Text.AlignVCenter
                text: Strings.tr("Radio Globe")
                color: panel.api.foreground
                font.family: panel.api.fontFamily
                font.pixelSize: 16; font.bold: true
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
                width: parent.width - favourites.width - 6; height: 32
                sourceComponent: panel.api.controls.textField
                onLoaded: {
                    item.placeholderText = Qt.binding(() => Strings.tr(({name: "Search stations by name", tag: "Search stations by tag", country: "Search countries"})[panel.searchMode]));
                    // Room for the search glyph on the left and the filter button on the right.
                    item.leftPadding = 32;
                    item.rightPadding = 38;
                    item.maximumLength = 100;
                    item.textChanged.connect(() => { panel.searchText = item.text; debounce.restart(); });
                    item.accepted.connect(() => {
                        debounce.stop();
                        // By country, Enter takes the first match.
                        if (panel.pickingCountry && panel.countryMatches.length) panel.chooseCountry(panel.countryMatches[0]);
                        else panel.runSearch();
                    });
                }
                Text {
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    text: "\u{F0349}"
                    color: panel.api.foreground
                    opacity: 0.6
                    font.family: panel.api.fontFamily
                    font.pixelSize: 15
                }
                RadioAction {
                    id: filterButton
                    objectName: "search-filter"
                    api: panel.api
                    anchors.right: parent.right; anchors.rightMargin: 2; anchors.verticalCenter: parent.verticalCenter
                    width: 28; height: 28; icon: true
                    text: "\u{F0236}"
                    description: Strings.tr("Search filter")
                    selected: panel.filterOpen
                    onClicked: panel.filterOpen = !panel.filterOpen
                }
            }
            RadioAction {
                id: favourites
                objectName: "favourites"
                api: panel.api; width: 110
                text: Strings.tr("Favourites"); selected: panel.favoritesOnly
                onClicked: { panel.filterOpen = false; if (panel.favoritesOnly) panel.closeFavorites(); else panel.favoritesOnly = true; }
            }
        }
        Row {
            id: explorer
            width: parent.width; height: 400
            spacing: 12
            RadioGlobe {
                id: globe
                api: panel.api
                width: Math.floor(explorer.width * 0.5)
                height: explorer.height
                countries: backend.countries
                selectedCode: panel.countryCode
                reduceMotion: panel.reduceMotion
                onChosen: country => panel.chooseCountry(country)
            }
            Column {
                id: stationColumn
                width: explorer.width - Math.floor(explorer.width * 0.5) - 12
                height: explorer.height
                spacing: 4
                // While Favourites shows: the way back to the list it replaced.
                Row {
                    id: favouritesHeading
                    width: parent.width; height: 28
                    visible: panel.favoritesOnly
                    spacing: 4
                    RadioAction {
                        objectName: "favourites-back"
                        api: panel.api
                        width: 28; height: 28; icon: true
                        text: "\u{F0141}"
                        description: Strings.tr("Back")
                        anchors.verticalCenter: parent.verticalCenter
                        onClicked: panel.closeFavorites()
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: Strings.tr("Favourites")
                        textFormat: Text.PlainText
                        color: panel.api.foreground
                        font.family: panel.api.fontFamily
                        font.pixelSize: 13; font.bold: true
                    }
                }
                Text {
                    id: status
                    width: parent.width
                    // Only when there is something to say: nothing chosen and nothing typed shows nothing.
                    visible: text !== ""
                    text: backend.error ? Strings.tr("Request failed") : backend.stale ? Strings.tr("Offline · showing saved countries") : backend.busy ? Strings.tr("Loading…") : panel.favoritesOnly ? "" : panel.pickingCountry ? "" : panel.searchText.trim() ? Strings.tr("Search results") : panel.countryName
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
                    height: parent.height - (status.visible ? status.height + parent.spacing : 0) - (favouritesHeading.visible ? favouritesHeading.height + parent.spacing : 0)
                    visible: !panel.pickingCountry
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: panel.displayed
                    ScrollBar.vertical: ScrollBar {}
                    delegate: StationRow {
                        required property var modelData
                        required property int index
                        width: list.width - 8
                        api: panel.api; station: modelData
                        favorite: backend.isFavorite(modelData)
                        playing: backend.playing !== null && backend.playing.station.stationuuid === modelData.stationuuid
                        enabled: !backend.busy
                        last: index === list.count - 1
                        onPlayRequested: { backend.action("play", modelData); panel.faceStation(modelData); }
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
                // By country: the countries whose name matches what is typed.
                ListView {
                    id: countryList
                    width: parent.width
                    height: parent.height - (status.visible ? status.height + parent.spacing : 0) - (favouritesHeading.visible ? favouritesHeading.height + parent.spacing : 0)
                    visible: panel.pickingCountry
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    model: panel.countryMatches
                    ScrollBar.vertical: ScrollBar {}
                    delegate: Item {
                        id: countryRow
                        required property var modelData
                        required property int index
                        width: countryList.width - 8
                        height: 36
                        RadioAction {
                            api: panel.api
                            width: parent.width; height: 28
                            anchors.verticalCenter: parent.verticalCenter
                            text: countryRow.modelData.name + " · " + countryRow.modelData.count
                            textAlignment: Text.AlignLeft
                            onClicked: panel.chooseCountry(countryRow.modelData)
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        width: parent.width
                        visible: panel.countryMatches.length === 0
                        text: Strings.tr("No countries match")
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
    }
    // The filter menu, above everything else; a click anywhere outside it closes it.
    MouseArea {
        anchors.fill: parent
        visible: panel.filterOpen
        z: 1
        onClicked: panel.filterOpen = false
    }
    SearchFilter {
        objectName: "search-filter-menu"
        visible: panel.filterOpen
        z: 2
        readonly property point anchor: panel.filterOpen ? filterButton.mapToItem(panel, filterButton.width, filterButton.height) : Qt.point(0, 0)
        x: Math.max(0, anchor.x - width); y: anchor.y + 4
        api: panel.api
        mode: panel.searchMode
        onChosen: mode => panel.chooseMode(mode)
    }
}
