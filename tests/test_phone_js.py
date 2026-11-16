"""Exercise the QML model and every bundled translation without a desktop."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

PLUGIN = Path(__file__).resolve().parents[1] / 'plugins/phone-link'


@unittest.skipUnless(shutil.which('node'), 'Node required for QML JavaScript tests')
class PhoneJavascriptTests(unittest.TestCase):
    def test_state_and_all_translations(self):
        script = r'''
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const folder = process.argv[1];
function load(name, context = {}) {
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(folder + "/" + name, "utf8").replace(".pragma library", ""), context);
    return context;
}
const state = load("PhoneState.js");
for (const invalid of ["", "null", "[]", "{}", '{"state":"odd","devices":[]}']) {
    assert.equal(state.parse(invalid), null);
}
const devices = [{name:"Offline",paired:true,reachable:false},
    {name:"Available",paired:false,reachable:true},
    {name:"Phone",paired:true,reachable:true,battery:80}];
const parsed = state.parse(JSON.stringify({state:"ready",devices:devices}));
assert.equal(state.connected(parsed).name, "Phone");
assert.equal(state.connected(null), null);
assert.notEqual(state.glyph("tablet"), state.glyph("phone"));
let locale = "en_US";
const strings = load("Strings.js", {Qt:{locale:() => ({name:locale})}});
assert.equal(strings.languages.length, 7);
for (const [source, values] of Object.entries(strings.entries)) {
    assert.equal(values.length, 7, source);
    for (const [index, language] of strings.languages.entries()) {
        locale = language;
        assert.ok(values[index].trim(), source + " " + language);
        assert.equal(strings.tr(source), values[index]);
    }
    locale = "en_US";
    assert.equal(strings.tr(source), source);
}
locale = "de_DE";
assert.equal(strings.tr("Pair"), "Koppeln");
locale = "pt_BR";
assert.equal(strings.tr("Send files"), "Enviar arquivos");
assert.equal(strings.tr("Other devices"), "Outros dispositivos");
assert.equal(strings.tr("Ring"), "Tocar");
assert.equal(strings.tr("Not shared by this phone"), "Não compartilhado por este telefone");
for (const stale of ["Actions", "Hide actions", "Ring my phone", "Disabled actions are not shared by this phone."]) {
    assert.ok(!Object.hasOwn(strings.entries, stale));
}
assert.equal(strings.tr("Eitr's firewall already lets KDE Connect through on your local network."),
    "O firewall do Eitr já permite o KDE Connect na sua rede local.");
assert.ok(!Object.hasOwn(strings.entries, "Hide"));
assert.ok(!Object.hasOwn(strings.entries, "Eitr firewall allows:"));
console.log(JSON.stringify({labels:Object.keys(strings.entries).length,languages:strings.languages.length}));
'''
        result = subprocess.run(['node', '-e', script, str(PLUGIN)], text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'labels': 37, 'languages': 7})


if __name__ == '__main__':
    unittest.main()
