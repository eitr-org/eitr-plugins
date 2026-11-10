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
    "disconnected": "Disconnected",
    "signed-out": "Signed out",
    "needs-approval": "Waiting for admin approval",
    "starting": "Starting…",
    "not-installed": "Not installed",
    "unavailable": "Status unavailable"
};

var connectionLabels = {
    "direct": "Direct",
    "relayed": "Relayed",
    "idle": "Idle",
    "offline": "Offline"
};

function isMobile(os) {
    return /^(ios|android)$/i.test(os || "");
}

// Bar glyphs: connected and disconnected network.
