import QtQuick
import Quickshell
import "." as Bar
import "phone" as Phone

ShellRoot {
    id: root
    property bool light: false
    property int phase: 0
    property var sample: SAMPLE
    property var edge: EDGE
    property var stopped: ({state: "stopped", devices: [], total: 0})
    property var snapshot: phase === 0 ? sample : phase === 1 ? stopped
        : phase === 2 ? ({state: "ready", devices: sample.devices.slice(0, 1), total: 1})
        : phase === 3 ? ({state: "ready", devices: sample.devices.slice(1), total: 3})
        : phase === 4 ? edge : ({state: "ready", devices: [], total: 0})
    property var received: []
    property var probeDevice: sample.devices[0]
    property var otherDevice: sample.devices[1]
    QtObject {
        id: fake
        property color foreground: root.light ? "#203b30" : "#e6f1e9"
        property color background: root.light ? "#f3f8f1" : "#10231c"
        property color accent: root.light ? "#32644c" : "#68aa87"
        property var palette: ({foreground: foreground, background: background, accent: accent})
        property string fontFamily: "JetBrainsMono Nerd Font"
        property int bodySize: 13
        property int headingSize: 16
        property int captionSize: 12
        property int radius: 4
        property string detail: ""
        property string streamLine: JSON.stringify(root.snapshot)
        property string dataText: streamLine
        property string dataError: ""
        property bool observed: true
        property var controls: ({button: button})
        signal streamReceived(string line)
        function runDataCommand() {}
    }
    Component { id: button; Bar.PanelButton { foreground: fake.foreground; text: "" } }
    FloatingWindow {
        implicitWidth: 440; implicitHeight: 1400; visible: true; color: fake.background
        Rectangle {
            id: canvas
            color: fake.background; width: 380; height: page.implicitHeight + 100
            Phone.PhonePanel { id: page; api: fake; x: 18; y: 70; width: 384 }
            Rectangle {
                id: icons
                x: 18; y: 18; width: 128; height: 36; color: fake.background
                Phone.PhoneBarIcon { id: connected; api: fake; x: 12; y: 6 }
                Phone.PhoneBarIcon {
                    api: QtObject {
                        property color foreground: fake.foreground
                        property color background: fake.background
                        property string fontFamily: fake.fontFamily
                        property int radius: 4
                        property string streamLine: JSON.stringify(root.stopped)
                        property string dataText: streamLine
                        property string detail: ""
                        signal streamReceived(string line)
                    }
                    x: 80; y: 6
                }
            }
        }
        Item {
            x: 10000; width: 384
            Phone.PhoneConnected {
                id: probe; api: fake; device: root.probeDevice
                onActionRequested: function(action, identifier, payload) { root.received.push({action, identifier, payload}); }
            }
            Phone.PhoneDevice {
                id: otherProbe; api: fake; device: root.otherDevice
                onActionRequested: function(action, identifier, payload) { root.received.push({action, identifier, payload}); }
            }
        }
    }
    function assert(condition, message) { if (!condition) throw new Error(message); }
    function findAll(item, name) {
        let matches = item.objectName === name ? [item] : [];
        for (const child of item.children || []) matches = matches.concat(findAll(child, name));
        return matches;
    }
    function find(item, name) {
        const matches = findAll(item, name);
        assert(matches.length > 0, "Missing " + name);
        return matches[0];
    }
    function hostButton(item) {
        const loader = item.children.find(child => child.item !== undefined);
        assert(loader && loader.item, "Missing shared button");
        return loader.item;
    }
    function press(item) {
        const buttonItem = hostButton(item);
        assert(buttonItem.enabled, "Pressed unavailable button");
        buttonItem.clicked();
    }
    function checkActions() {
        root.probeDevice = root.sample.devices[0];
        root.otherDevice = root.sample.devices[1];
        root.received = [];
        for (const action of ["send", "clipboard", "ring", "ping"]) {
            press(find(probe, "action-" + action));
            const request = root.received.pop();
            assert(request.action === action && request.identifier === "phone", "Wrong action target");
        }
        const browse = find(probe, "action-browse");
        assert(!hostButton(browse).enabled && browse.explanation === "Not shared by this phone", "Unsupported action");
        probe.busy = true;
        assert(!hostButton(find(probe, "action-send")).enabled, "Busy tile enabled");
        assert(!hostButton(find(probe, "unpair")).enabled, "Busy unpair enabled");
        probe.busy = false;
        const supported = JSON.parse(JSON.stringify(root.probeDevice));
        supported.plugins.push("kdeconnect_sftp");
        root.probeDevice = supported;
        press(browse);
        assert(root.received.pop().action === "browse", "Browse target");
        press(find(probe, "unpair"));
        assert(root.received.length === 0 && find(probe, "confirm-unpair").visible, "Unpair skipped confirmation");
        press(find(probe, "cancel-unpair"));
        assert(root.received.length === 0 && !find(probe, "confirm-unpair").visible, "Cancel unpair");
        press(find(probe, "unpair"));
        press(find(probe, "confirm-unpair"));
        const unpair = root.received.pop();
        assert(unpair.action === "unpair" && unpair.identifier === "phone" && unpair.payload.confirmed, "Unpair payload");
        for (const action of ["accept", "reject"]) {
            press(find(otherProbe, action + "-pairing"));
            const request = root.received.pop();
            assert(request.action === action && request.identifier === "request", "Pairing action");
        }
        assert(find(otherProbe, "pairing-code").text === "123456", "Pairing code missing");
        root.otherDevice = Object.assign({}, root.sample.devices[3], {outgoing: true, verification: "654321"});
        assert(find(otherProbe, "pairing-code").visible, "Outgoing code hidden");
        assert(!hostButton(find(otherProbe, "device-action")).enabled, "Pending pair enabled");
        root.otherDevice = root.sample.devices[3];
        press(find(otherProbe, "device-action"));
        assert(root.received.pop().action === "pair", "Pair action");
        root.otherDevice = root.sample.devices[2];
        press(find(otherProbe, "device-action"));
        press(find(otherProbe, "confirm-unpair"));
        assert(root.received.pop().payload.confirmed, "Offline unpair");
    }
    function checkLayout() {
        const count = page.connectedDevices.length;
        assert(findAll(page, "connected-header").length === count, "Connected card count");
        assert(find(page, "setup-help").visible === (count === 0), "Setup help visibility");
        assert(find(page, "firewall-help").visible === (root.phase === 1 || root.phase === 5), "Firewall visibility");
        assert(find(page, "other-devices").visible === (page.otherDevices.length > 0), "Other devices section");
        for (const grid of findAll(page, "action-grid")) {
            assert(grid.columns === 3, "Grid columns");
            const send = find(grid, "action-send"), clipboard = find(grid, "action-clipboard");
            const ring = find(grid, "action-ring"), ping = find(grid, "action-ping"), browse = find(grid, "action-browse");
            assert(send.width === clipboard.width && send.width === browse.width, "Unequal tiles");
            assert(send.y === ring.y && ping.y === browse.y && ping.y > send.y, "Grid rows");
            assert(ring.x > clipboard.x && clipboard.x > send.x, "Grid columns misplaced");
            assert(browse.x + browse.width <= grid.width, "Clipped tiles");
        }
        const captions = findAll(page, "battery-caption");
        if (root.phase === 0 || root.phase === 2) assert(captions[0].text === "44% · On battery", "Battery state");
        if (root.phase === 4) {
            assert(captions[0].text.indexOf("Charging") !== -1, "Charging state");
            assert(captions[1].text === "Connected", "Unknown battery fabricated");
        }
    }
    function checkDetail() {
        const device = page.connectedDevices[0];
        const expected = device ? device.name + (device.battery === null ? "" : " · " + device.battery + "%") : "No phone connected";
        assert(fake.detail === expected, "Bad host detail: " + fake.detail);
        if (root.phase !== 0) return;
        const unknownBattery = JSON.parse(JSON.stringify(root.sample));
        unknownBattery.devices[0].battery = null;
        connected.update(JSON.stringify(unknownBattery));
        assert(fake.detail === "Galaxy S23 Ultra", "Unknown battery detail");
        connected.update("invalid");
        assert(fake.detail === "Galaxy S23 Ultra", "Invalid status replaced detail");
        connected.update(JSON.stringify(root.stopped));
        assert(fake.detail === "No phone connected", "Disconnected detail");
        connected.update(JSON.stringify(root.sample));
        assert(fake.detail === expected, "Reconnected detail");
    }
    Timer {
        interval: 500; running: true; repeat: true
        property bool saving: false
        onTriggered: {
            if (saving) return;
            if (root.phase === 0) root.checkActions();
            root.checkLayout();
            root.checkDetail();
            const theme = root.light ? "light" : "dark";
            const state = ["panel", "setup", "connected", "other", "devices", "empty"][root.phase];
            saving = true;
            canvas.grabToImage(function(capture) {
                root.assert(capture.saveToFile("OUTPUT/" + state + "-" + theme + ".png"), "Save failed");
                icons.grabToImage(function(bar) {
                    if (root.phase === 0) root.assert(bar.saveToFile("OUTPUT/bar-" + theme + ".png"), "Bar save failed");
                    if (root.phase === 5 && root.light) { console.log("PHONE_RENDER_OK"); Qt.quit(); }
                    if (root.phase === 5) { root.phase = 0; root.light = true; }
                    else root.phase += 1;
                    saving = false;
                });
            });
        }
    }
}
