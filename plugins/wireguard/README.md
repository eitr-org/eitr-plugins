# WireGuard

WireGuard on the Eitr bar. Place the WireGuard icon from **Control Center > Plugins**
(it joins the right-side icon group). The official WireGuard logo is shown at full
strength while a tunnel is connected and dimmed while disconnected or unavailable.
The reviewed manifest installs the official `wireguard-tools` package.

## Panel

Click the bar icon for the panel:

- **Heading**: connection state and **Import a config**, which opens Eitr's task
  terminal to review and import a `.conf` file.
- **Active tunnel**: the connected tunnel's name, endpoint (with a copy button),
  transfer and latest handshake.
- **Tunnels**: every imported tunnel with its connect/disconnect switch and a remove
  button that asks for inline confirmation before deleting the tunnel.

Status comes from `status.py --json` (`wg show` plus saved NetworkManager WireGuard
profiles or `wg-quick` tunnels, three-second deadlines, at most 100 tunnels). The bar
icon refreshes every 15 seconds while placed; the open panel every 5 seconds, with no
background polling while nothing shows them.

## Actions

The panel runs `action.py` detached with fixed argv. Connecting, disconnecting and
removing a tunnel use `nmcli` on NetworkManager or `pkexec` (`/usr/bin/wg-quick` and
`/usr/bin/rm`) on iwd, so the desktop's authentication popup handles administrator
approval and the bar never asks for passwords.

Import a config asks for a full `.conf` path and reviews it before importing. Hooks,
SaveConfig and unsupported fields are refused. Keys and command errors are never
displayed. NetworkManager imports the profile with `nmcli` and disables autoconnect.
On iwd, Eitr's narrow root importer requests sudo approval in the task terminal and
saves the config root-owned, mode 0600, under `/etc/wireguard`; existing files are
never overwritten. Imports keep the tunnel disconnected.

## Walker rows

Import a config, Connect a tunnel, Disconnect a tunnel, Remove a tunnel, and Status.

"WireGuard" and the "WireGuard" logo are registered trademarks of Jason A. Donenfeld.
This plugin is not made or endorsed by the WireGuard project; the logo only identifies the
protocol it controls.
