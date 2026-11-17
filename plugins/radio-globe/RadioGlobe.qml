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
    // The country under the pointer (its dot or its shape) and the one whose stations show.
    property var hovered: null
    property string selectedCode: ""
    property var shapes: []
    // The finer shapes, read the first time the globe is zoomed in.
    property var detailShapes: []
    property bool wantDetail: false
    readonly property real maximumZoom: 4
    readonly property bool detailed: zoom >= 1.5 && detailShapes.length > 0
    readonly property var drawnShapes: detailed ? detailShapes : shapes
    readonly property color foreground: api.palette.foreground || api.foreground
    readonly property color accent: api.palette.color4 || api.accent
    readonly property real radius: Math.min(width, height) * 0.43 * zoom
    signal chosen(var country)
    // Turns the globe so a chosen country faces the viewer, the short way round.
    function faceCountry(country) {
        if (country && country.location) facePlace(country.location[0], country.location[1]);
    }
    function facePlace(placeLatitude, placeLongitude) {
        interacted = true;
        const latitudeTarget = Math.max(-75, Math.min(75, placeLatitude));
        let longitudeTarget = placeLongitude;
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
    onShapesChanged: canvas.requestPaint()
    onSelectedCodeChanged: canvas.requestPaint()
    onDetailedChanged: canvas.requestPaint()
    onHoveredChanged: canvas.requestPaint()
    onForegroundChanged: canvas.requestPaint()
    onAccentChanged: canvas.requestPaint()
    FileView {
        path: Qt.resolvedUrl("data/shapes.json").toString().replace(/^file:\/\//, "")
        onLoaded: {
            try { globe.shapes = GlobeMath.prepare(JSON.parse(text())); }
            catch (error) { console.warn("Radio Globe country shapes could not be read"); }
        }
    }
    FileView {
        path: globe.wantDetail ? Qt.resolvedUrl("data/shapes-detail.json").toString().replace(/^file:\/\//, "") : ""
        onLoaded: {
            try { globe.detailShapes = GlobeMath.prepare(JSON.parse(text())); }
            catch (error) { console.warn("Radio Globe detailed country shapes could not be read"); }
        }
    }
    // The country with stations under a pointer position: its dot first, then its shape.
    function countryUnder(pointerX, pointerY) {
        const dot = GlobeMath.hit(countries, pointerX, pointerY, radius, width / 2, height / 2, longitude, latitude);
        if (dot) return dot;
        const place = GlobeMath.unproject((pointerX - width / 2) / radius, (height / 2 - pointerY) / radius, longitude, latitude);
        if (!place) return null;
        const code = GlobeMath.countryAt(drawnShapes, place[0], place[1]);
        return code ? countries.find(country => country.code === code) || null : null;
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
            // A ring as a closed path; points behind the globe are pulled onto its edge, so a
            // country across the horizon still fills up to it.
            function ring(points) {
                for (let index = 0; index < points.length; index += 2) {
                    const point = project(points[index], points[index + 1]);
                    let x = point[0], y = point[1];
                    if (point[2] < 0) { const length = Math.hypot(x, y) || 1; x /= length; y /= length; }
                    if (index === 0) context.moveTo(centerX + x * radius, centerY - y * radius);
                    else context.lineTo(centerX + x * radius, centerY - y * radius);
                }
                context.closePath();
            }
            // Zoomed in, only part of the front half shows; polygons beyond it are skipped.
            const corner = Math.hypot(width, height) / 2;
            const reach = corner >= radius ? 90 : Math.asin(corner / radius) * 180 / Math.PI;
            context.beginPath();
            context.arc(centerX, centerY, radius, 0, Math.PI * 2);
            context.fillStyle = Qt.alpha(globe.accent, 0.05);
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
            // Land in a soft tint with thin borders; the hovered country lighter, the chosen one in the accent.
            context.fillRule = Qt.OddEvenFill;
            const hoveredCode = globe.hovered ? globe.hovered.code : "";
            const highlighted = [];
            for (const country of globe.drawnShapes) {
                const emphasis = country.code === globe.selectedCode ? 2 : country.code === hoveredCode ? 1 : 0;
                context.beginPath();
                let drawn = false;
                for (const polygon of country.polygons) {
                    if (GlobeMath.distance(polygon.center[0], polygon.center[1], globe.longitude, globe.latitude) > Math.min(90, reach) + polygon.reach) continue;
                    for (const points of polygon.rings) ring(points);
                    drawn = true;
                }
                if (!drawn) continue;
                if (emphasis) { highlighted.push([country, emphasis]); continue; }
                context.fillStyle = Qt.alpha(globe.foreground, 0.09);
                context.fill();
                context.lineWidth = 0.8;
                context.strokeStyle = Qt.alpha(globe.foreground, 0.32);
                context.stroke();
            }
            // Drawn last so their whole border shows over the neighbours'.
            for (const entry of highlighted) {
                context.beginPath();
                for (const polygon of entry[0].polygons)
                    if (GlobeMath.distance(polygon.center[0], polygon.center[1], globe.longitude, globe.latitude) <= Math.min(90, reach) + polygon.reach)
                        for (const points of polygon.rings) ring(points);
                context.fillStyle = entry[1] === 2 ? Qt.alpha(globe.accent, 0.45) : Qt.alpha(globe.foreground, 0.18);
                context.fill();
                context.lineWidth = entry[1] === 2 ? 1.4 : 1;
                context.strokeStyle = entry[1] === 2 ? globe.accent : Qt.alpha(globe.foreground, 0.55);
                context.stroke();
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
            if (!pressed) globe.hovered = globe.countryUnder(mouse.x, mouse.y);
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
        visible: !!globe.hovered
        text: globe.hovered ? globe.hovered.name + " · " + globe.hovered.count : ""
        textFormat: Text.PlainText
        elide: Text.ElideRight
        color: globe.foreground
        opacity: 0.72
        font.family: globe.api.fontFamily
        font.pixelSize: 11
    }
}
