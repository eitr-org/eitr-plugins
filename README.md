# Eitr plugins

Official plugins for [Eitr](https://github.com/eitr-org/eitr), reviewed by the Eitr project.

| Plugin | What it does |
|---|---|
| [Visualizer](plugins/visualizer) | A desktop audio visualizer that moves with whatever is playing, in a Wave or Bars style |
| [Lofi Radio](plugins/lofi-radio) | Lofi music through lowfi, controlled from the bar |
| [WireGuard](plugins/wireguard) | WireGuard on the bar: import, connect, inspect and remove tunnels on iwd or NetworkManager |
| [NetworkManager VPN](plugins/networkmanager-vpn) | NetworkManager VPN on the bar: OpenVPN, OpenConnect and WireGuard profiles, connection details and import |
| [Tailscale](plugins/tailscale) | Tailscale on the bar: connect, see your devices, copy their addresses and send or receive files |

## Install

In Walker, open **Install > Plugins > Add Plugin…**, paste
`https://github.com/eitr-org/eitr-plugins`, and pick the plugins you want. Each one is
reviewed separately before it is installed, pinned to the exact commit you approved,
and updated only after you review its changes with **Update Plugins** (Control Center >
Plugins or Install > Plugins). System Update only tells you how many plugin updates
are waiting.

## Writing a plugin

Read Eitr's plugin guide, `distro/PLUGINS.md` in the Eitr repository. Each plugin
lives in its own folder under `plugins/` with its `eitr-plugin.json`, and is listed in
`eitr-plugins.json`.

## Checks

Run `bash tools/check.sh` from this repository. The offline tests use the sibling
`../eitr` checkout's manifest validator, install-review serializer and WireGuard
validator. Networking, privilege requests and file transfers are mocked.

## License

MIT. See [LICENSE](LICENSE).
