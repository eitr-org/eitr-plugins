pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Window
import Quickshell
import Quickshell.Io
import "Strings.js" as Strings
import "VisualizerState.js" as State

Item {
    id: root
    required property var api
    implicitWidth: 900
    implicitHeight: 180
    property string style: "wave"
    // "accent": one colour from the theme accent; "palette": a gradient through the theme's
    // yellow, red, magenta and blue (color3, color1, color5, color4), low to high.
    property string colors: "accent"
    readonly property string activeStyle: State.normalizeStyle(style)
    readonly property string activeColors: State.normalizeColors(colors)
    readonly property var paletteStops: {
        const palette = api.palette || {};
        const picked = ["color3", "color1", "color5", "color4"].map(function(name) { return palette[name]; }).filter(function(value) { return !!value; });
        return picked.length === 4 ? picked : [secondAccent, api.accent, brightAccent, brightAccent];
    }
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
    property bool saveQueued: false
    property string lastWrittenText: ""
    readonly property color reflectionShadow: Qt.alpha(core, 0.08)

    function mix(first, second, amount) {
        return Qt.rgba(first.r * (1 - amount) + second.r * amount,
                       first.g * (1 - amount) + second.g * amount,
                       first.b * (1 - amount) + second.b * amount, 1);
    }
    function clearGradients() {
        canvas.barGradient = null;
        canvas.waveGradient = null;
        canvas.reflectionGradient = null;
        canvas.mirrorGradient = null;
        canvas.ringGradient = null;
        canvas.dotsGradient = null;
    }
    function flushSave() {
        if (!saveQueued || !ready || !persistOptions) return;
        saveQueued = false;
        const payload = JSON.stringify({version: 1, style: activeStyle, colors: activeColors}) + "\n";
        lastWrittenText = payload;
        preferences.setText(payload);
    }
    function save() {
        if (ready && persistOptions && !saveQueued) {
            saveQueued = true;
            Qt.callLater(flushSave);
        }
    }
    onStyleChanged: { settled = false; canvas.requestPaint(); save(); updateMenu(); }
    onColorsChanged: { clearGradients(); canvas.requestPaint(); save(); updateMenu(); }
    onPaletteStopsChanged: { clearGradients(); canvas.requestPaint(); }
    onCoreChanged: { canvas.reflectionGradient = null; canvas.requestPaint(); }
    onSecondAccentChanged: { clearGradients(); canvas.requestPaint(); }
    onBrightAccentChanged: { clearGradients(); canvas.requestPaint(); }
    FileView {
        id: preferences
        path: root.persistOptions ? (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/eitr-plugin-visualizer/options.json" : ""
        atomicWrites: true
        printErrors: false
        watchChanges: true
        onFileChanged: reload()
        onSaved: if (root.saveQueued) root.flushSave()
        onLoaded: {
            const rawText = text();
            if (rawText === root.lastWrittenText || root.saveQueued) {
                root.ready = true;
                return;
            }
            const parsed = State.parseOptions(rawText);
            if (parsed) {
                root.ready = false;
                root.style = parsed.style;
                root.colors = parsed.colors;
            } else {
                console.warn("Visualizer: ignoring invalid options JSON");
            }
            root.ready = true;
        }
        onLoadFailed: root.ready = true
        onSaveFailed: console.warn("Visualizer: could not save options")
    }
    Component.onCompleted: {
        api.spectrumBars = count;
        api.spectrumFrameRate = 30;
        api.spectrumSmoothing = false;
        if (!persistOptions && api.instanceData && typeof api.instanceData === "object") {
            if ("style" in api.instanceData) root.style = State.normalizeStyle(api.instanceData.style);
            if ("colors" in api.instanceData) root.colors = State.normalizeColors(api.instanceData.colors);
        }
        updateMenu();
        if (api.audioActive && api.spectrum && api.spectrum.length > 0) {
            const warmupSteps = persistOptions ? 1 : 6;
            for (let step = 0; step < warmupSteps; ++step)
                advance();
        }
    }
    Connections {
        target: root.api
        function onSpectrumChanged() { root.settled = false; }
        function onAudioActiveChanged() { root.settled = false; }
    }
    // Fixed storage is reused for smoothing, gravity and five history frames.
    function advance() {
        const source = api.spectrum || [];
        const dt = timer.interval / 1000;
        let moving = false;
        head = (head + 1) % 5;
        for (let index = 0; index < count; ++index) {
            history[head * count + index] = levels[index];
            const raw = api.audioActive && source.length > 0 ? source[Math.min(source.length - 1, Math.floor(index * source.length / count))] : 0;
            const target = Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0;
            if (activeStyle !== "wave") {
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
        property var waveGradient: null
        property var reflectionGradient: null
        property var mirrorGradient: null
        property var ringGradient: null
        property var dotsGradient: null
        onWidthChanged: { ringGradient = null; dotsGradient = null; requestPaint(); }
        onHeightChanged: { root.clearGradients(); requestPaint(); }
        // The palette runs low to high over the span, so taller peaks reach later colours.
        function addStops(gradient) {
            if (root.activeColors === "palette") {
                const stops = root.paletteStops;
                for (let index = 0; index < stops.length; ++index)
                    gradient.addColorStop(index / (stops.length - 1), stops[index]);
            } else {
                gradient.addColorStop(0, root.secondAccent);
                gradient.addColorStop(0.55, root.api.accent);
                gradient.addColorStop(1, root.brightAccent);
            }
            return gradient;
        }
        function linearSpanGradient(context, bottom, top) {
            return addStops(context.createLinearGradient(0, bottom, 0, top));
        }
        function symmetricGradient(context, fullHeight) {
            const gradient = context.createLinearGradient(0, 0, 0, fullHeight);
            if (root.activeColors === "palette") {
                const stops = root.paletteStops;
                const last = stops.length - 1;
                for (let index = 0; index < stops.length; ++index) {
                    const offset = (index / last) * 0.5;
                    gradient.addColorStop(0.5 - offset, stops[index]);
                    if (offset > 0) gradient.addColorStop(0.5 + offset, stops[index]);
                }
            } else {
                gradient.addColorStop(0, root.brightAccent);
                gradient.addColorStop(0.225, root.api.accent);
                gradient.addColorStop(0.5, root.secondAccent);
                gradient.addColorStop(0.775, root.api.accent);
                gradient.addColorStop(1, root.brightAccent);
            }
            return gradient;
        }
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
            const baseInk = root.activeColors === "palette" ? root.paletteStops[0] : root.api.accent;
            if (root.activeStyle === "bars") {
                if (!barGradient) barGradient = linearSpanGradient(context, height, 0);
                context.fillStyle = barGradient;
                const step = width / root.count;
                for (let index = 0; index < root.count; ++index) {
                    const barHeight = Math.round(root.levels[index] * (height - 2));
                    context.fillRect(Math.floor(index * step), height - barHeight,
                                     Math.max(0, Math.floor((index + 1) * step) - Math.floor(index * step) - 1), barHeight);
                }
                return;
            }
            if (root.activeStyle === "mirror") {
                const layout = State.mirrorGeometry(width, height, root.levels, root.count);
                context.fillStyle = Qt.alpha(baseInk, 0.22);
                context.fillRect(0, Math.floor(layout.centerY), width, 1);
                if (!mirrorGradient) mirrorGradient = symmetricGradient(context, height);
                context.fillStyle = mirrorGradient;
                for (let index = 0; index < layout.bars.length; ++index) {
                    const bar = layout.bars[index];
                    if (bar.height > 0)
                        context.fillRect(bar.x, bar.y, bar.width, bar.height);
                }
                return;
            }
            if (root.activeStyle === "ring") {
                const ring = State.ringGeometry(width, height, root.levels, root.count);
                context.beginPath();
                context.arc(ring.cx, ring.cy, ring.baseRadius, 0, Math.PI * 2);
                context.strokeStyle = Qt.alpha(baseInk, 0.28);
                context.lineWidth = ring.baseStrokeWidth;
                context.stroke();
                if (!ringGradient)
                    ringGradient = addStops(context.createRadialGradient(ring.cx, ring.cy, ring.baseRadius, ring.cx, ring.cy, ring.outerRadius));
                context.strokeStyle = ringGradient;
                context.lineWidth = ring.barWidth;
                context.lineCap = "round";
                for (let index = 0; index < ring.bars.length; ++index) {
                    const bar = ring.bars[index];
                    if (bar.length > 0) {
                        context.beginPath();
                        context.moveTo(bar.x0, bar.y0);
                        context.lineTo(bar.x1, bar.y1);
                        context.stroke();
                    }
                }
                return;
            }
            if (root.activeStyle === "dots") {
                const layout = State.dotsGeometry(width, height, root.levels, root.count);
                if (!dotsGradient)
                    dotsGradient = linearSpanGradient(context, layout.bottomY + layout.dotRadius, Math.max(0, layout.topY - layout.dotRadius));
                const faintInk = Qt.alpha(baseInk, 0.20);
                for (let index = 0; index < layout.dots.length; ++index) {
                    const dot = layout.dots[index];
                    context.fillStyle = faintInk;
                    context.beginPath();
                    context.arc(dot.cx, dot.bottomY, layout.baseRadius, 0, Math.PI * 2);
                    context.fill();
                    context.fillStyle = dotsGradient;
                    context.beginPath();
                    context.arc(dot.cx, dot.cy, layout.dotRadius, 0, Math.PI * 2);
                    context.fill();
                }
                return;
            }
            if (root.activeColors === "palette" && !waveGradient) waveGradient = linearSpanGradient(context, height * 0.69, height * 0.09);
            const ink = root.activeColors === "palette" ? waveGradient : root.core;
            context.fillStyle = ink;
            context.strokeStyle = ink;
            context.shadowColor = root.activeColors === "palette" ? root.paletteStops[0] : root.core;
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
                const near = root.activeColors === "palette" ? root.paletteStops[0] : root.core;
                reflectionGradient.addColorStop(0, Qt.alpha(near, 0.33));
                reflectionGradient.addColorStop(1, Qt.alpha(near, 0));
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
            api.setMenu(State.menuEntries(activeStyle, activeColors, Strings.tr));
    }
    Connections {
        target: root.api
        ignoreUnknownSignals: true
        function onMenuTriggered(id) {
            if (State.isStyleOption(id)) root.style = State.normalizeStyle(id);
            else if (State.isColorOption(id)) root.colors = State.normalizeColors(id);
        }
    }
}
