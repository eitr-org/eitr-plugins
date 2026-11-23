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
testVisualizerStateAndTranslations();
console.log("widget helper tests passed");
