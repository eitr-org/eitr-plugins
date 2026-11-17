pragma ComponentBehavior: Bound
import QtQuick
import Quickshell.Io
import "GlobeMath.js" as GlobeMath
import "Strings.js" as Strings

Item {
    id: globe
    required property var api
    property var countries: []
    property bool reduceMotion: true
    property real longitude: -25
    property real latitude: 15
    property real zoom: 1
    property bool interacted: false
    property var hovered: null
    property var outlines: []
    // The finer outline, read the first time the globe is zoomed in.
    property var detailOutlines: []
    property bool wantDetail: false
    readonly property real maximumZoom: 4
    readonly property bool detailed: zoom >= 1.5 && detailOutlines.length > 0
    readonly property color foreground: api.palette.foreground || api.foreground
    readonly property color accent: api.palette.color4 || api.accent
    readonly property real radius: Math.min(width, height) * 0.43 * zoom
    signal chosen(var country)
    // Turns the globe so a chosen country faces the viewer, the short way round.
    function faceCountry(country) {
        if (!country || !country.location) return;
        interacted = true;
        const latitudeTarget = Math.max(-75, Math.min(75, country.location[0]));
        let longitudeTarget = country.location[1];
        while (longitudeTarget - longitude > 180) longitudeTarget -= 360;
        while (longitudeTarget - longitude < -180) longitudeTarget += 360;
        turn.stop();
        if (reduceMotion) { longitude = longitudeTarget; latitude = latitudeTarget; return; }
        turnLongitude.to = longitudeTarget; turnLatitude.to = latitudeTarget;
        turn.start();
    }
    ParallelAnimation {
        id: turn
        NumberAnimation { id: turnLongitude; target: globe; property: "longitude"; duration: 700; easing.type: Easing.InOutCubic }
        NumberAnimation { id: turnLatitude; target: globe; property: "latitude"; duration: 700; easing.type: Easing.InOutCubic }
    }
    implicitWidth: 300
    implicitHeight: 340
    onLongitudeChanged: canvas.requestPaint()
    onLatitudeChanged: canvas.requestPaint()
    onZoomChanged: {
        if (zoom >= 1.5) wantDetail = true;
        canvas.requestPaint();
    }
    onCountriesChanged: canvas.requestPaint()
    onOutlinesChanged: canvas.requestPaint()
    onDetailedChanged: canvas.requestPaint()
    onHoveredChanged: canvas.requestPaint()
    onForegroundChanged: canvas.requestPaint()
    onAccentChanged: canvas.requestPaint()
    FileView {
        path: Qt.resolvedUrl("data/land.json").toString().replace(/^file:\/\//, "")
        onLoaded: {
            try { globe.outlines = GlobeMath.prepare(JSON.parse(text())); }
            catch (error) { console.warn("Radio Globe land outline could not be read"); }
        }
    }
    FileView {
        path: globe.wantDetail ? Qt.resolvedUrl("data/land-detail.json").toString().replace(/^file:\/\//, "") : ""
        onLoaded: {
            try { globe.detailOutlines = GlobeMath.prepare(JSON.parse(text())); }
            catch (error) { console.warn("Radio Globe detailed land outline could not be read"); }
        }
    }
    // Zooms by a factor, keeping the place under the pointer where it is (or the centre).
    function zoomBy(factor, pointerX, pointerY) {
        const next = Math.max(0.85, Math.min(maximumZoom, zoom * factor));
        if (next === zoom) return;
        const place = GlobeMath.unproject((pointerX - width / 2) / radius, (height / 2 - pointerY) / radius, longitude, latitude);
        if (place && next > zoom) {
            // Turning part of the way to the place keeps it close to the pointer as the globe grows.
            const share = 1 - zoom / next;
            let target = place[0];
            while (target - longitude > 180) target -= 360;
            while (target - longitude < -180) target += 360;
            longitude += (target - longitude) * share;
            latitude = Math.max(-75, Math.min(75, latitude + (place[1] - latitude) * share));
        }
        zoom = next;
    }
    Timer {
        interval: 80
        repeat: true
        running: globe.api.observed && globe.visible && !globe.interacted && !globe.reduceMotion && !pointer.containsMouse
        onTriggered: globe.longitude = (globe.longitude + 0.12) % 360
    }
    Canvas {
        id: canvas
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const context = getContext("2d");
            context.reset();
            const radius = globe.radius;
            const centerX = width / 2;
            const centerY = height / 2;
            const project = (lon, lat) => GlobeMath.project(lon, lat, globe.longitude, globe.latitude);
            // Points are flat [longitude, latitude, longitude, latitude, …].
            function line(points) {
                context.beginPath();
                let visible = false;
                for (let index = 0; index < points.length; index += 2) {
                    const point = project(points[index], points[index + 1]);
                    if (point[2] >= 0) {
                        if (visible) context.lineTo(centerX + point[0] * radius, centerY - point[1] * radius);
                        else context.moveTo(centerX + point[0] * radius, centerY - point[1] * radius);
                    }
                    visible = point[2] >= 0;
                }
                context.stroke();
            }
            // Zoomed in, only part of the front half shows; rings beyond it are skipped.
            const corner = Math.hypot(width, height) / 2;
            const reach = corner >= radius ? 90 : Math.asin(corner / radius) * 180 / Math.PI;
            context.beginPath();
            context.arc(centerX, centerY, radius, 0, Math.PI * 2);
            context.fillStyle = Qt.alpha(globe.accent, 0.07);
            context.fill();
            context.strokeStyle = Qt.alpha(globe.foreground, 0.23);
            context.lineWidth = 1;
            context.stroke();
            context.save();
            context.clip();
            context.strokeStyle = Qt.alpha(globe.foreground, 0.09);
            for (let latitude = -60; latitude <= 60; latitude += 30) {
                const points = [];
                for (let longitude = -180; longitude <= 180; longitude += 3) points.push(longitude, latitude);
                line(points);
            }
            for (let longitude = -180; longitude < 180; longitude += 30) {
                const points = [];
                for (let latitude = -90; latitude <= 90; latitude += 3) points.push(longitude, latitude);
                line(points);
            }
            context.lineWidth = 1.4;
            context.strokeStyle = Qt.alpha(globe.foreground, 0.5);
            for (const ring of globe.detailed ? globe.detailOutlines : globe.outlines) {
                if (GlobeMath.distance(ring.center[0], ring.center[1], globe.longitude, globe.latitude) > reach + ring.reach) continue;
                line(ring.points);
            }
            for (const country of globe.countries) {
                if (!country.location) continue;
                const point = project(country.location[1], country.location[0]);
                if (point[2] <= 0.02) continue;
                context.beginPath();
                context.arc(centerX + point[0] * radius, centerY - point[1] * radius, GlobeMath.dotRadius(country.count), 0, Math.PI * 2);
                context.fillStyle = Qt.alpha(globe.accent, globe.hovered && globe.hovered.code === country.code ? 1 : 0.72);
                context.fill();
                context.strokeStyle = globe.api.background;
                context.lineWidth = 1.2;
                context.stroke();
            }
            context.restore();
        }
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        // The panel scrolls; without this its scroll area takes the drag over after a few pixels.
        preventStealing: true
        property real previousX: 0
        property real previousY: 0
        property real distance: 0
        cursorShape: pressed ? Qt.ClosedHandCursor : globe.hovered ? Qt.PointingHandCursor : Qt.OpenHandCursor
        onPressed: mouse => {
            turn.stop();
            globe.interacted = true;
            previousX = mouse.x; previousY = mouse.y; distance = 0;
        }
        onPositionChanged: mouse => {
            if (pressed) {
                const deltaX = mouse.x - previousX;
                const deltaY = mouse.y - previousY;
                // The same drag covers less of the world when zoomed in, so it feels the same.
                globe.longitude -= deltaX * 0.5 / globe.zoom;
                globe.latitude = Math.max(-75, Math.min(75, globe.latitude + deltaY * 0.4 / globe.zoom));
                distance += Math.abs(deltaX) + Math.abs(deltaY);
                previousX = mouse.x; previousY = mouse.y;
            }
            globe.hovered = GlobeMath.hit(globe.countries, mouse.x, mouse.y, globe.radius, width / 2, height / 2, globe.longitude, globe.latitude);
        }
        onClicked: mouse => { if (distance < 5 && globe.hovered) globe.chosen(globe.hovered); }
        onExited: globe.hovered = null
        onWheel: wheel => {
            globe.interacted = true;
            // A mouse notch (120) zooms by a fifth; touchpads send smaller steps.
            globe.zoomBy(Math.pow(1.2, wheel.angleDelta.y / 120), wheel.x, wheel.y);
        }
    }
    Text {
        objectName: "globe-hint"
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        width: parent.width
        horizontalAlignment: Text.AlignHCenter
        text: globe.hovered ? globe.hovered.name + " · " + globe.hovered.count : Strings.tr("Drag · Scroll to zoom")
        textFormat: Text.PlainText
        elide: Text.ElideRight
        color: globe.foreground
        opacity: 0.72
        font.family: globe.api.fontFamily
        font.pixelSize: 11
    }
}
