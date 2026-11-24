.pragma library

function message(payload) {
    return ["message", JSON.stringify(payload)];
}

function resetTime(epoch) {
    return Qt.formatDateTime(new Date(epoch * 1000), Qt.locale().dateTimeFormat(Locale.ShortFormat));
}
