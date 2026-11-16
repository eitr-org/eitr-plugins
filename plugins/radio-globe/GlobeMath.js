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
