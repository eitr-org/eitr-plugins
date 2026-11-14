.pragma library

function parse(text) {
    try {
        const data = JSON.parse(text);
        data.cities = data.cities.map(city => Array.isArray(city)
            ? {zone:city[0], label:city[1], time24:city[2], time12:city[3], day:city[4], offset:city[5]} : city);
        return data;
    } catch (error) { return null; }
}

function latest(api) {
    const command = parse(api.dataText);
    const stream = parse(api.streamLine);
    if (command && (!stream || command.updated > stream.updated)) return command;
    return stream ? Object.assign({}, stream, {zones: command && command.zones ? command.zones : []}) : null;
}

function time(city, format) {
    return format === "24h" ? city.time24 : city.time12;
}

function settings(status) {
    return {barCount: status.barCount, cities: status.cities.map(city => ({zone: city.zone, label: city.label}))};
}
