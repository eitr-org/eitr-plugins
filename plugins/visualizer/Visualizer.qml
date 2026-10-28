pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io

Item {
    id: root
    required property var api
    implicitWidth: 900
    implicitHeight: 180
    property string style: "wave"
    // Disable persistence for embedding and synthetic render harnesses.
    property bool persistOptions: true
    readonly property int count: 64
    readonly property color core: mix(api.accent, api.foreground, 0.72)
    readonly property color secondAccent: mix(api.accent, api.background, 0.55)
    readonly property color brightAccent: mix(api.accent, api.foreground, 0.45)
    property var levels: new Float32Array(count)
    property var velocity: new Float32Array(count)
    property var history: new Float32Array(count * 5)
    property int head: 0
    property int ticks: 0
    property bool settled: false
    property bool ready: false
    readonly property color reflectionNear: Qt.alpha(core, 0.33)
    readonly property color reflectionFar: Qt.alpha(core, 0)
    readonly property color reflectionShadow: Qt.alpha(core, 0.08)

    function mix(first, second, amount) {
        return Qt.rgba(first.r * (1 - amount) + second.r * amount,
                       first.g * (1 - amount) + second.g * amount,
                       first.b * (1 - amount) + second.b * amount, 1);
    }
    function save() {
        if (ready && persistOptions)
            preferences.setText(JSON.stringify({version: 1, style: style}) + "\n");
    }
    onStyleChanged: { settled = false; save(); updateMenu(); }
    onCoreChanged: { canvas.reflectionGradient = null; canvas.requestPaint(); }
    onSecondAccentChanged: { canvas.barGradient = null; canvas.requestPaint(); }
    onBrightAccentChanged: { canvas.barGradient = null; canvas.requestPaint(); }
    FileView {
        id: preferences
        path: root.persistOptions ? (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/eitr-plugin-visualizer/options.json" : ""
        printErrors: false
        watchChanges: true
        onFileChanged: reload()
        onLoaded: {
            try {
                const saved = JSON.parse(text());
                if (saved.version === 1) {
                    root.ready = false;
                    root.style = saved.style === "terminal" ? "terminal" : "wave";
                }
            } catch (error) { console.warn("Visualizer: ignoring invalid options JSON"); }
            root.ready = true;
        }
        onLoadFailed: root.ready = true
        onSaveFailed: console.warn("Visualizer: could not save options")
    }
    Component.onCompleted: {
        api.spectrumBars = count;
        api.spectrumFrameRate = 30;
        api.spectrumSmoothing = false;
        updateMenu();
    }
    Connections {
        target: root.api
        function onSpectrumChanged() { root.settled = false; }
        function onAudioActiveChanged() { root.settled = false; }
    }
    // Fixed storage is reused for smoothing, gravity and five history frames.
    function advance() {
        const source = api.spectrum;
        const dt = timer.interval / 1000;
        let moving = false;
        head = (head + 1) % 5;
        for (let index = 0; index < count; ++index) {
            history[head * count + index] = levels[index];
            const raw = api.audioActive && source.length > 0 ? source[Math.min(source.length - 1, Math.floor(index * source.length / count))] : 0;
            const target = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0;
            if (style === "terminal") {
                if (target >= levels[index]) { levels[index] = target; velocity[index] = 0; }
                else {
                    velocity[index] += 5 * dt;
                    levels[index] = Math.max(target, levels[index] - velocity[index] * dt);
                }
            } else {
                levels[index] += (target - levels[index]) * (1 - Math.exp(-dt / (target > levels[index] ? 0.045 : 0.18)));
            }
            if (levels[index] < 0.003 && target === 0) levels[index] = 0;
            moving = moving || levels[index] > 0;
        }
        ticks = moving ? 0 : ticks + 1;
        settled = !api.audioActive && ticks > 6;
        canvas.requestPaint();
    }
    Timer {
        id: timer
        interval: Math.ceil(1000 / Math.max(1, Math.min(60, root.api.spectrumFrameRate)))
        running: root.visible && root.enabled && root.opacity > 0 && !root.settled
        repeat: true
        onTriggered: root.advance()
    }
    Canvas {
        id: canvas
        anchors.fill: parent
        renderStrategy: Canvas.Immediate
        property var barGradient: null
        property var reflectionGradient: null
        onWidthChanged: requestPaint()
        onHeightChanged: { barGradient = null; reflectionGradient = null; requestPaint(); }
        // Frequency zero is at the centre; each side samples the same curve.
        function amplitude(point, offset) {
            const index = Math.min(root.count - 1, Math.abs(point - (root.count - 1)));
            const value = offset < 0 ? root.levels[index] : root.history[offset + index];
            const taper = Math.sin(Math.PI * point / (2 * (root.count - 1)));
            return (1.2 + value * height * 0.60) * taper;
        }
        function path(context, offset, reflection) {
            const total = 2 * root.count - 1;
            const step = width / (total - 1);
            const baseline = height * 0.69;
            const scale = reflection ? 0.4 : -1;
            context.beginPath();
            context.moveTo(0, baseline);
            for (let point = 0; point < total - 1; ++point) {
                const previous = amplitude(Math.max(0, point - 1), offset);
                const current = amplitude(point, offset);
                const next = amplitude(point + 1, offset);
                const after = amplitude(Math.min(total - 1, point + 2), offset);
                context.bezierCurveTo((point + 1 / 3) * step, baseline + (current + (next - previous) / 6) * scale,
                                     (point + 2 / 3) * step, baseline + (next - (after - current) / 6) * scale,
                                     (point + 1) * step, baseline + next * scale);
            }
            context.lineTo(width, baseline);
            context.closePath();
        }
        onPaint: {
            const context = getContext("2d");
            context.reset();
            context.clearRect(0, 0, width, height);
            if (root.style === "terminal") {
                if (!barGradient) {
                    barGradient = context.createLinearGradient(0, height, 0, 0);
                    barGradient.addColorStop(0, root.secondAccent);
                    barGradient.addColorStop(0.55, root.api.accent);
                    barGradient.addColorStop(1, root.brightAccent);
                }
                context.fillStyle = barGradient;
                const step = width / root.count;
                for (let index = 0; index < root.count; ++index) {
                    const barHeight = Math.round(root.levels[index] * (height - 2));
                    context.fillRect(Math.floor(index * step), height - barHeight,
                                     Math.max(0, Math.floor((index + 1) * step) - Math.floor(index * step) - 1), barHeight);
                }
                return;
            }
            context.fillStyle = root.core;
            context.strokeStyle = root.core;
            context.shadowColor = root.core;
            for (let age = 4; age >= 0; --age) {
                context.globalAlpha = 0.025 + (4 - age) * 0.025;
                context.lineWidth = 3 + age;
                path(context, ((root.head - age + 5) % 5) * root.count, false);
                context.fill();
                context.stroke();
            }
            path(context, -1, false);
            // Nested translucent strokes approximate bloom without a full-surface blur.
            for (let halo = 4; halo > 0; --halo) {
                context.globalAlpha = 0.035;
                context.lineWidth = halo * 3;
                context.stroke();
            }
            context.globalAlpha = 0.85;
            context.fill();
            context.lineWidth = 1.3;
            context.stroke();
            if (!reflectionGradient) {
                reflectionGradient = context.createLinearGradient(0, height * 0.69, 0, height * 0.96);
                reflectionGradient.addColorStop(0, root.reflectionNear);
                reflectionGradient.addColorStop(1, root.reflectionFar);
            }
            context.globalAlpha = 1;
            context.fillStyle = reflectionGradient;
            context.lineWidth = 2;
            context.shadowColor = root.reflectionShadow;
            path(context, -1, true);
            context.fill();
            context.globalAlpha = 0.16;
            context.strokeStyle = reflectionGradient;
            context.stroke();
        }
    }
    // Eitr's widget menu shows these options next to its own size and layer entries.
    function updateMenu() {
        if (typeof api.setMenu === "function")
            api.setMenu([{id: "wave", text: "Wave", checked: style === "wave"},
                         {id: "terminal", text: "Terminal", checked: style === "terminal"}]);
    }
    Connections {
        target: root.api
        ignoreUnknownSignals: true
        function onMenuTriggered(id) {
            if (id === "wave" || id === "terminal") root.style = id;
        }
    }
}
