.pragma library

var STYLES = [
    {id: "wave", label: "Wave"},
    {id: "bars", label: "Bars"},
    {id: "ring", label: "Ring"},
    {id: "mirror", label: "Mirror"},
    {id: "dots", label: "Dots"}
];

var COLOR_MODES = [
    {id: "accent", label: "Accent"},
    {id: "palette", label: "Palette"}
];

function normalizeStyle(value) {
    if (value === "terminal" || value === "bars") return "bars";
    if (value === "wave" || value === "ring" || value === "mirror" || value === "dots") return value;
    return "bars";
}

function normalizeColors(value) {
    return value === "palette" ? "palette" : "accent";
}

function parseOptions(text) {
    if (typeof text !== "string" || !text.trim()) return null;
    try {
        const saved = JSON.parse(text);
        if (!saved || typeof saved !== "object" || saved.version !== 1) return null;
        return {
            style: normalizeStyle(saved.style),
            colors: normalizeColors(saved.colors)
        };
    } catch (error) {
        return null;
    }
}

function isStyleOption(identifier) {
    return identifier === "terminal" || STYLES.some(function(choice) { return choice.id === identifier; });
}

function isColorOption(identifier) {
    return COLOR_MODES.some(function(choice) { return choice.id === identifier; });
}

function menuEntries(currentStyle, currentColors, translate) {
    const activeStyle = normalizeStyle(currentStyle);
    const activeColors = normalizeColors(currentColors);
    const tr = typeof translate === "function" ? translate : function(label) { return label; };
    const entries = STYLES.map(function(choice) {
        return {
            id: choice.id,
            text: tr(choice.label),
            checked: activeStyle === choice.id
        };
    });
    const colorGroup = tr("Colors");
    for (let index = 0; index < COLOR_MODES.length; ++index) {
        const choice = COLOR_MODES[index];
        entries.push({
            id: choice.id,
            text: tr(choice.label),
            checked: activeColors === choice.id,
            group: colorGroup
        });
    }
    return entries;
}

function clampLevel(value) {
    return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
}

function sampleRange(levels, count, startBin, endBin) {
    if (!levels || count <= 0) return 0;
    const first = Math.max(0, Math.min(count - 1, startBin));
    const limit = Math.max(first + 1, Math.min(count, endBin));
    let sum = 0;
    for (let index = first; index < limit; ++index)
        sum += clampLevel(levels[index]);
    return sum / (limit - first);
}

function ringGeometry(width, height, levels, count) {
    const totalBars = Math.max(2, count || 64);
    const half = Math.floor(totalBars / 2);
    const side = Math.max(0, Math.min(width, height));
    const cx = width / 2;
    const cy = height / 2;
    const outerRadius = Math.max(6, side * 0.46);
    const baseRadius = outerRadius * 0.48;
    const maxBarLength = Math.max(2, outerRadius - baseRadius);
    const slotArc = (2 * Math.PI * baseRadius) / totalBars;
    const barWidth = Math.max(1.4, Math.min(8, slotArc * 0.62));
    const baseStrokeWidth = Math.max(1.2, side * 0.012);
    const bars = [];
    for (let stepIndex = 0; stepIndex < totalBars; ++stepIndex) {
        const halfIndex = stepIndex < half ? stepIndex : totalBars - 1 - stepIndex;
        const startBin = Math.floor(halfIndex * totalBars / half);
        const endBin = Math.max(startBin + 1, Math.floor((halfIndex + 1) * totalBars / half));
        const level = sampleRange(levels, totalBars, startBin, endBin);
        const barLength = Math.round(level * maxBarLength);
        const angle = -Math.PI / 2 + (stepIndex + 0.5) * (Math.PI * 2 / totalBars);
        const cos = Math.cos(angle);
        const sin = Math.sin(angle);
        bars.push({
            index: stepIndex,
            halfIndex: halfIndex,
            angle: angle,
            level: level,
            length: barLength,
            x0: cx + cos * baseRadius,
            y0: cy + sin * baseRadius,
            x1: cx + cos * (baseRadius + barLength),
            y1: cy + sin * (baseRadius + barLength)
        });
    }
    return {
        cx: cx,
        cy: cy,
        side: side,
        baseRadius: baseRadius,
        outerRadius: outerRadius,
        maxBarLength: maxBarLength,
        barWidth: barWidth,
        baseStrokeWidth: baseStrokeWidth,
        bars: bars
    };
}

function mirrorGeometry(width, height, levels, count) {
    const totalBars = Math.max(1, count || 64);
    const centerY = height / 2;
    const halfAvailable = Math.max(1, (height - 2) / 2);
    const step = width / totalBars;
    const bars = [];
    for (let index = 0; index < totalBars; ++index) {
        const x = Math.floor(index * step);
        const barWidth = Math.max(1, Math.floor((index + 1) * step) - x - 1);
        const level = levels ? clampLevel(levels[index]) : 0;
        const halfHeight = Math.round(level * halfAvailable);
        bars.push({
            x: x,
            y: Math.round(centerY - halfHeight),
            width: barWidth,
            height: halfHeight * 2,
            halfHeight: halfHeight,
            level: level
        });
    }
    return {
        centerY: centerY,
        halfAvailable: halfAvailable,
        bars: bars
    };
}

function dotsGeometry(width, height, levels, count) {
    const totalBins = Math.max(1, count || 64);
    const dotCount = Math.max(16, Math.min(totalBins, Math.floor(width / 8)));
    const step = width / dotCount;
    const dotRadius = Math.max(2, Math.min(6, step * 0.34, height * 0.09));
    const baseRadius = Math.max(1.2, dotRadius * 0.45);
    const padY = Math.max(3, dotRadius + 2);
    const bottomY = Math.max(padY, height - padY);
    const topY = Math.min(bottomY, padY);
    const travel = Math.max(0, bottomY - topY);
    const dots = [];
    for (let index = 0; index < dotCount; ++index) {
        const startBin = Math.floor(index * totalBins / dotCount);
        const endBin = Math.max(startBin + 1, Math.floor((index + 1) * totalBins / dotCount));
        const level = sampleRange(levels, totalBins, startBin, endBin);
        dots.push({
            cx: (index + 0.5) * step,
            cy: bottomY - level * travel,
            bottomY: bottomY,
            level: level
        });
    }
    return {
        dotCount: dotCount,
        dotRadius: dotRadius,
        baseRadius: baseRadius,
        bottomY: bottomY,
        topY: topY,
        travel: travel,
        dots: dots
    };
}

if (typeof module !== "undefined") {
    module.exports = {
        STYLES: STYLES,
        COLOR_MODES: COLOR_MODES,
        normalizeStyle: normalizeStyle,
        normalizeColors: normalizeColors,
        parseOptions: parseOptions,
        isStyleOption: isStyleOption,
        isColorOption: isColorOption,
        menuEntries: menuEntries,
        clampLevel: clampLevel,
        sampleRange: sampleRange,
        ringGeometry: ringGeometry,
        mirrorGeometry: mirrorGeometry,
        dotsGeometry: dotsGeometry
    };
}
