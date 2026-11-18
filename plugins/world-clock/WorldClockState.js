.pragma library

function parse(text) {
    try {
        const data = JSON.parse(text);
        data.cities = data.cities.map(city => Array.isArray(city)
            ? {zone:city[0], label:city[1], time24:city[2], time12:city[3], day:city[4], offset:city[5], flag:city[6] || "", key:city[7]} : city);
        return data;
    } catch (error) { return null; }
}

function latest(api) {
    const command = parse(api.dataText);
    const stream = parse(api.streamLine);
    if (command && (!stream || command.updated > stream.updated)) return command;
    return stream ? merge(stream, command) : null;
}

function merge(current, previous) {
    if (!current) return previous;
    return Object.assign({}, current, {cities: current.cities.map(city => {
        const old = previous && previous.cities.find(saved => city.key ? saved.key === city.key : saved.zone === city.zone && (city.name ? saved.name === city.name : previous.cities.filter(candidate => candidate.zone === city.zone).length === 1));
        return Object.assign({}, old || {}, city);
    }), zones: []});
}

function time(city, format) {
    return format === "24h" ? city.time24 : city.time12;
}

function settings(status) {
    return {barCount: status.barCount, cities: status.cities.map(city => (city.name && city.country ? {zone: city.zone, label: city.label, name: city.name, country: city.country} : {zone: city.zone, label: city.label}))};
}
