import QtQuick
import QtQuick.Shapes

// The NetworkManager VPN shield-and-arrow emblem from icon.svg.
Shape {
    id: logo
    property color color: "white"
    property real size: 18
    implicitWidth: size
    implicitHeight: size
    width: size
    height: size
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
        fillColor: "transparent"
        strokeColor: logo.color
        strokeWidth: 1.55
        capStyle: ShapePath.RoundCap
        joinStyle: ShapePath.RoundJoin
        scale: Qt.size(logo.size / 128, logo.size / 128)
        PathSvg {
            path: "M64 12 108 30v32c0 26-26 45-44 54C46 107 20 88 20 62V30Z M44 64h40m-12-12 12 12-12 12"
        }
    }
}
