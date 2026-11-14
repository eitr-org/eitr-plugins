const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../plugins/world-clock/WorldClockState.js"), "utf8").replace(/^\.pragma library\n/, "");
const state = vm.createContext({});
vm.runInContext(source, state);
const catalog = {updated: 1, barCount: 1, zones: ["Europe/Lisbon"], cities: []};
const stream = {updated: 2, barCount: 2, cities: [["Europe/Lisbon", "LIS", "14:05", "2:05 PM", "Today", "+3 h"]]};
const api = {dataText: JSON.stringify(catalog), streamLine: JSON.stringify(stream)};
const current = state.latest(api);
assert.equal(current.cities[0].zone, "Europe/Lisbon");
assert.equal(current.cities[0].label, "LIS");
assert.equal(state.time(current.cities[0], "24h"), "14:05");
assert.equal(state.time(current.cities[0], "12h"), "2:05 PM");
assert.equal(current.zones.length, 0);
assert.equal(state.settings(current).barCount, 2);
assert.deepEqual(JSON.parse(JSON.stringify(state.settings(current).cities)), [{zone: "Europe/Lisbon", label: "LIS"}]);
api.dataText = JSON.stringify({...catalog, updated: 3});
assert.equal(state.latest(api).cities.length, 0);
assert.equal(state.parse("not JSON"), null);
console.log("World clock stream decoding, catalog merge and time-format checks passed");

const rich = state.merge(current, {cities:[{zone:"Europe/Lisbon", name:"Lisbon", country:"PT"}]});
assert.equal(rich.cities[0].name, "Lisbon");
assert.equal(state.settings(rich).cities[0].country, "PT");
assert.equal(state.parse(JSON.stringify({cities:[["Asia/Tokyo", "TYO", "23:05", "11:05 PM", "Today", "+12 h", "🇯🇵"]]})).cities[0].flag, "🇯🇵");

const shared = {cities: [
    {key:"state-key", zone:"America/Los_Angeles", name:"California", country:"US", label:"CAL"},
    {key:"city-key", zone:"America/Los_Angeles", name:"Los Angeles", country:"US", label:"LAX"}
]};
const duplicates = state.parse(JSON.stringify({barCount:10, cities: [
    ["America/Los_Angeles", "LAX", "14:05", "2:05 PM", "Today", "+3 h", "🇺🇸", "city-key"],
    ["America/Los_Angeles", "CAL", "14:05", "2:05 PM", "Today", "+3 h", "🇺🇸", "state-key"]
]}));
const merged = state.merge(duplicates, shared);
assert.equal(merged.cities[0].name, "Los Angeles");
assert.equal(merged.cities[1].name, "California");
assert.equal(state.settings(merged).cities[1].name, "California");
assert.equal(state.merge({cities:[]}, shared).cities.length, 0);
console.log("Duplicate-zone identity and state metadata checks passed");
