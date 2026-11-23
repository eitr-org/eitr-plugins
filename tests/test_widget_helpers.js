"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function loadQmlLibrary(relativePath) {
    const filePath = path.resolve(__dirname, "..", relativePath);
    const source = fs.readFileSync(filePath, "utf8").replace(/^\s*\.pragma\s+library\s*\r?\n/, "");
    const sandbox = {module: {exports: {}}};
    vm.runInNewContext(source, sandbox, {filename: filePath});
    return sandbox.module.exports;
}

const NotesColors = loadQmlLibrary("plugins/notes/NotesColors.js");
const HardwareState = loadQmlLibrary("plugins/hardware/HardwareState.js");
const VisualizerState = loadQmlLibrary("plugins/visualizer/VisualizerState.js");
const VisualizerStrings = loadQmlLibrary("plugins/visualizer/Strings.js");

function testNotesColors() {
    assert.strictEqual(NotesColors.COLORS.length, 5);
    assert.strictEqual(NotesColors.normalizeColor("blue"), "blue");
    assert.strictEqual(NotesColors.normalizeColor("theme"), "theme");
    assert.strictEqual(NotesColors.normalizeColor("invalid-color"), "yellow");
    for (const choice of NotesColors.COLORS) {
        for (const mode of ["light", "dark"]) {
            const palette = NotesColors.softPalette(choice.id, mode === "light");
            for (const key of ["paper", "header", "border", "ink", "placeholder", "swatch"]) {
                assert.ok(typeof palette[key] === "string" && palette[key].startsWith("#"),
                    choice.id + "." + mode + "." + key);
            }
        }
    }
}

function testHardwareFormattingAndThresholds() {
    assert.strictEqual(HardwareState.normalizeMode("compact"), "compact");
    assert.strictEqual(HardwareState.normalizeMode("detailed"), "detailed");
    assert.strictEqual(HardwareState.normalizeMode("unknown"), "detailed");

    assert.strictEqual(HardwareState.formatSpeed(null), "—");
    assert.strictEqual(HardwareState.formatSpeed(undefined), "—");
    assert.strictEqual(HardwareState.formatSpeed(-10), "—");
    assert.strictEqual(HardwareState.formatSpeed(0), "0 B/s");
    assert.strictEqual(HardwareState.formatSpeed(512), "512 B/s");
    assert.strictEqual(HardwareState.formatSpeed(1500), "1.5 KB/s");
    assert.strictEqual(HardwareState.formatSpeed(12400000), "12.4 MB/s");
    assert.strictEqual(HardwareState.formatSpeed(250000000), "250 MB/s");
    assert.strictEqual(HardwareState.formatSpeed(1800000000), "1.8 GB/s");

    assert.strictEqual(HardwareState.usageLevel(null), "muted");
    assert.strictEqual(HardwareState.usageLevel(0), "normal");
    assert.strictEqual(HardwareState.usageLevel(74.9), "normal");
    assert.strictEqual(HardwareState.usageLevel(75), "warning");
    assert.strictEqual(HardwareState.usageLevel(89.9), "warning");
    assert.strictEqual(HardwareState.usageLevel(90), "critical");

    assert.strictEqual(HardwareState.extractTemp({rows: [["Frequency / temperature", "3.85 GHz · 48°C"]]}), "48°C");
    assert.strictEqual(HardwareState.extractTemp({rows: [["Temperature", "44.0 °C"]]}), "44°C");
    assert.strictEqual(HardwareState.extractTemp({rows: [["Frequency / temperature", "3.85 GHz · Unavailable"]]}), "");
    assert.strictEqual(HardwareState.extractTemp({rows: [["Temperature", "Unavailable"]]}), "");
    assert.strictEqual(HardwareState.extractTemp({rows: []}), "");
}

function testHardwareSummaryVariants() {
    assert.strictEqual(HardwareState.summarize(null).state, "loading");
    assert.strictEqual(HardwareState.summarize({status: "loading", sections: []}).message, "Loading...");

    const failed = HardwareState.summarize({
        status: "error",
        error: "timeout",
        sections: [],
        network: {status: "error", download: null, upload: null}
    });
    assert.strictEqual(failed.state, "error");
    assert.strictEqual(failed.message, "Hardware information unavailable");

    const full = HardwareState.summarize({
        status: "ready",
        error: "",
        sections: [
            {title: "CPU", name: "AMD Ryzen 7 7840U", usage: 34, rows: [["Cores / threads", "8 / 16"], ["Frequency / temperature", "3.85 GHz · 52°C"]]},
            {title: "GPU", name: "AMD Radeon 780M", usage: 18, rows: [["VRAM used / total", "1.2 / 4.0 GiB"], ["Temperature", "47.0 °C"]]},
            {title: "RAM", name: "Memory", usage: 46, rows: [["Used / total", "14.4 GiB / 31.3 GiB"], ["Available", "16.9 GiB"]]},
            {title: "Storage", name: "Root", usage: 55, rows: [["Type / device", "NVMe SSD · nvme0n1"], ["Used / total", "240 GiB / 460 GiB"], ["Free", "220 GiB"]]}
        ],
        network: {status: "ready", download: 12400000, upload: 1800000, interfaces: ["wlan0"], connection: "Studio WiFi"}
    });
    assert.strictEqual(full.state, "ready");
    assert.deepStrictEqual(Array.from(full.metrics.map(metric => metric.title)), ["CPU", "GPU", "RAM", "Storage"]);
    assert.strictEqual(full.metrics[0].temp, "52°C");
    assert.strictEqual(full.metrics[1].temp, "47°C");
    assert.strictEqual(full.network.downloadText, "12.4 MB/s");
    assert.strictEqual(full.network.uploadText, "1.8 MB/s");

    const noGpuNoTemp = HardwareState.summarize({
        status: "ready",
        error: "",
        sections: [
            {title: "CPU", name: "Intel Core i5-1240P", usage: 82, rows: [["Cores / threads", "12 / 16"], ["Frequency / temperature", "Unavailable"]]},
            {title: "GPU", name: "GPU telemetry unavailable", usage: null, rows: []},
            {title: "RAM", name: "Memory", usage: 92, rows: [["Used / total", "14.7 GiB / 16.0 GiB"], ["Available", "1.3 GiB"]]},
            {title: "Storage", name: "Root", usage: 40, rows: [["Used / total", "100 GiB / 250 GiB"], ["Free", "150 GiB"]]}
        ],
        network: {status: "loading", download: null, upload: null, interfaces: ["enp4s0"], connection: ""}
    });
    assert.strictEqual(noGpuNoTemp.state, "ready");
    assert.deepStrictEqual(Array.from(noGpuNoTemp.metrics.map(metric => metric.title)), ["CPU", "RAM", "Storage"]);
    assert.strictEqual(noGpuNoTemp.metrics[0].temp, "");
    assert.strictEqual(noGpuNoTemp.metrics[0].level, "warning");
    assert.strictEqual(noGpuNoTemp.metrics[1].level, "critical");
    assert.strictEqual(noGpuNoTemp.network.downloadText, "—");
    assert.strictEqual(noGpuNoTemp.network.connection, "enp4s0");
}

function testVisualizerStateAndTranslations() {
    assert.deepStrictEqual(
        Array.from(VisualizerState.STYLES.map(function(item) { return item.id; })),
        ["wave", "bars", "ring", "mirror", "dots"]
    );
    assert.strictEqual(VisualizerState.normalizeStyle("wave"), "wave");
    assert.strictEqual(VisualizerState.normalizeStyle("bars"), "bars");
    assert.strictEqual(VisualizerState.normalizeStyle("terminal"), "bars");
    assert.strictEqual(VisualizerState.normalizeStyle("ring"), "ring");
    assert.strictEqual(VisualizerState.normalizeStyle("mirror"), "mirror");
    assert.strictEqual(VisualizerState.normalizeStyle("dots"), "dots");
    assert.strictEqual(VisualizerState.normalizeStyle("unknown"), "bars");
    assert.strictEqual(VisualizerState.normalizeStyle(""), "bars");
    assert.strictEqual(VisualizerState.normalizeStyle(null), "bars");

    assert.strictEqual(VisualizerState.normalizeColors("accent"), "accent");
    assert.strictEqual(VisualizerState.normalizeColors("palette"), "palette");
    assert.strictEqual(VisualizerState.normalizeColors("other"), "accent");

    assert.deepStrictEqual(
        JSON.parse(JSON.stringify(VisualizerState.parseOptions('{"version":1,"style":"wave","colors":"palette"}'))),
        {style: "wave", colors: "palette"}
    );
    assert.deepStrictEqual(
        JSON.parse(JSON.stringify(VisualizerState.parseOptions('{"version":1,"style":"terminal","colors":"accent"}'))),
        {style: "bars", colors: "accent"}
    );
    assert.deepStrictEqual(
        JSON.parse(JSON.stringify(VisualizerState.parseOptions('{"version":1,"style":"mystery","colors":"unknown"}'))),
        {style: "bars", colors: "accent"}
    );
    assert.strictEqual(VisualizerState.parseOptions('{"version":2,"style":"wave"}'), null);
    assert.strictEqual(VisualizerState.parseOptions("not-json"), null);

    const levels = new Array(64);
    for (let index = 0; index < 64; ++index)
        levels[index] = (index + 1) / 64;

    const wideRing = VisualizerState.ringGeometry(900, 180, levels, 64);
    const squareRing = VisualizerState.ringGeometry(180, 180, levels, 64);
    assert.strictEqual(wideRing.cx, 450);
    assert.strictEqual(wideRing.cy, 90);
    assert.strictEqual(wideRing.side, 180);
    assert.strictEqual(wideRing.baseRadius, squareRing.baseRadius);
    assert.strictEqual(wideRing.outerRadius, squareRing.outerRadius);
    assert.strictEqual(wideRing.bars.length, 64);
    for (let index = 0; index < 32; ++index) {
        const rightBar = wideRing.bars[index];
        const leftBar = wideRing.bars[63 - index];
        assert.strictEqual(rightBar.length, leftBar.length);
        assert.ok(Math.abs((rightBar.x1 - wideRing.cx) + (leftBar.x1 - wideRing.cx)) < 1e-6);
        assert.ok(Math.abs(rightBar.y1 - leftBar.y1) < 1e-6);
    }

    const mirror = VisualizerState.mirrorGeometry(320, 160, levels, 64);
    assert.strictEqual(mirror.centerY, 80);
    assert.strictEqual(mirror.bars.length, 64);
    const lastMirror = mirror.bars[63];
    assert.strictEqual(lastMirror.height, lastMirror.halfHeight * 2);
    assert.strictEqual(lastMirror.y, 80 - lastMirror.halfHeight);

    const smallDots = VisualizerState.dotsGeometry(128, 80, levels, 64);
    const wideDots = VisualizerState.dotsGeometry(900, 180, levels, 64);
    assert.strictEqual(smallDots.dotCount, 16);
    assert.strictEqual(wideDots.dotCount, 64);
    assert.ok(wideDots.dots[63].cy < wideDots.dots[0].cy);

    assert.strictEqual(VisualizerStrings.languages.length, 7);
    for (const label of ["Wave", "Bars", "Ring", "Mirror", "Dots", "Accent", "Palette", "Colors"]) {
        assert.strictEqual(VisualizerStrings.tr(label, "en_US"), label);
        for (const lang of VisualizerStrings.languages) {
            const translated = VisualizerStrings.tr(label, lang);
            assert.ok(typeof translated === "string" && translated.trim().length > 0, label + "." + lang);
        }
    }
}

testNotesColors();
testHardwareFormattingAndThresholds();
testHardwareSummaryVariants();
testVisualizerStateAndTranslations();
console.log("widget helper tests passed");
