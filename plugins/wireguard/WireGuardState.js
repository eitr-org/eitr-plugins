.pragma library

// Parses status.py's JSON; null while there is no usable reply.
function parse(text) {
    if (!text)
        return null;
    try {
        const value = JSON.parse(text);
        return value && typeof value === "object" && typeof value.state === "string" ? value : null;
    } catch (error) {
        return null;
    }
}

var stateLabels = {
    "connected": "Connected",
    "connecting": "Connecting…",
    "disconnected": "Disconnected",
    "not-installed": "Not installed",
    "unavailable": "Status unavailable"
};
