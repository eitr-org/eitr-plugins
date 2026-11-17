.pragma library

function project(longitude, latitude, centerLongitude, centerLatitude) {
    const radians = Math.PI / 180;
    const relative = (longitude - centerLongitude) * radians;
    const phi = latitude * radians;
    const center = centerLatitude * radians;
    return [Math.cos(phi) * Math.sin(relative),
            Math.cos(center) * Math.sin(phi) - Math.sin(center) * Math.cos(phi) * Math.cos(relative),
            Math.sin(center) * Math.sin(phi) + Math.cos(center) * Math.cos(phi) * Math.cos(relative)];
}

// The place under a point of the globe's disc, as [longitude, latitude]; null off the globe.
function unproject(x, y, centerLongitude, centerLatitude) {
    const squared = x * x + y * y;
    if (squared > 1) return null;
    const radians = Math.PI / 180;
    const depth = Math.sqrt(1 - squared);
    const center = centerLatitude * radians;
    const latitude = Math.asin(Math.max(-1, Math.min(1, y * Math.cos(center) + depth * Math.sin(center))));
    const relative = Math.atan2(x, depth * Math.cos(center) - y * Math.sin(center));
    return [centerLongitude + relative / radians, latitude / radians];
}

// Each outline with its centre and reach (degrees), so drawing can skip rings out of view.
function prepare(rings) {
    const radians = Math.PI / 180;
    return rings.map(ring => {
        let x = 0, y = 0, z = 0;
        for (let index = 0; index < ring.length; index += 2) {
            const longitude = ring[index] * radians, latitude = ring[index + 1] * radians;
            x += Math.cos(latitude) * Math.cos(longitude); y += Math.cos(latitude) * Math.sin(longitude); z += Math.sin(latitude);
        }
        const length = Math.hypot(x, y, z) || 1;
        x /= length; y /= length; z /= length;
        let reach = 0;
        for (let index = 0; index < ring.length; index += 2) {
            const longitude = ring[index] * radians, latitude = ring[index + 1] * radians;
            const dot = x * Math.cos(latitude) * Math.cos(longitude) + y * Math.cos(latitude) * Math.sin(longitude) + z * Math.sin(latitude);
            reach = Math.max(reach, Math.acos(Math.max(-1, Math.min(1, dot))));
        }
        return {points: ring, center: [Math.atan2(y, x) / radians, Math.asin(z) / radians], reach: reach / radians};
    });
}

// Angle in degrees between two places.
function distance(firstLongitude, firstLatitude, secondLongitude, secondLatitude) {
    const radians = Math.PI / 180;
    const dot = Math.sin(firstLatitude * radians) * Math.sin(secondLatitude * radians)
        + Math.cos(firstLatitude * radians) * Math.cos(secondLatitude * radians) * Math.cos((firstLongitude - secondLongitude) * radians);
    return Math.acos(Math.max(-1, Math.min(1, dot))) / radians;
}

function dotRadius(count) { return Math.min(8, 2.5 + Math.log(1 + Math.max(0, count)) / 2); }

function hit(countries, pointerX, pointerY, radius, centerX, centerY, longitude, latitude) {
    let nearest = null;
    let distance = Infinity;
    for (const country of countries) {
        if (!country.location) continue;
        const point = project(country.location[1], country.location[0], longitude, latitude);
        if (point[2] <= 0.02) continue;
        const deltaX = pointerX - (centerX + point[0] * radius);
        const deltaY = pointerY - (centerY - point[1] * radius);
        const squared = deltaX * deltaX + deltaY * deltaY;
        if (squared < Math.pow(dotRadius(country.count) + 5, 2) && squared < distance) {
            nearest = country;
            distance = squared;
        }
    }
    return nearest;
}
