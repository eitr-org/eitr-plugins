.pragma library

function parse(line) {
    try {
        const state = JSON.parse(line);
        if (!state || !Array.isArray(state.devices)
            || ["missing", "stopped", "ready", "unavailable"].indexOf(state.state) === -1) return null;
        return state;
    } catch (error) { return null; }
}

function connected(state) {
    return state ? state.devices.find(device => device.paired && device.reachable) || null : null;
}

function glyph(type) {
    return type === "tablet" ? "\u{F04F6}" : type === "desktop" || type === "tv" ? "\u{F01B2}"
        : type === "laptop" ? "\u{F0322}" : "\u{F011C}";
}
