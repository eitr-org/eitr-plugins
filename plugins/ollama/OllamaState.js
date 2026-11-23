.pragma library
function parse(value) {
    try { const data = JSON.parse(value); return data && Array.isArray(data.loaded) ? data : null; }
    catch (error) { return null; }
}
function size(value) {
    return value >= 1000000000 ? (value / 1000000000).toFixed(1) + " GB"
        : Math.round(value / 1000000) + " MB";
}
