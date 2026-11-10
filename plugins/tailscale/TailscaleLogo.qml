import QtQuick

// Tailscale's nine-dot logo: the middle row and the bottom centre are solid, the rest faint.
Grid {
    id: logo
    property color color: "white"
    property int dot: 4
    readonly property var solidDots: [3, 4, 5, 7]
    columns: 3
    spacing: Math.max(1, Math.round(dot / 2))
    Repeater {
        model: 9
        Rectangle {
            required property int index
            width: logo.dot
            height: logo.dot
            radius: logo.dot / 2
            color: logo.color
            opacity: logo.solidDots.indexOf(index) >= 0 ? 1 : 0.35
        }
    }
}
