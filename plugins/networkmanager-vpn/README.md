# NetworkManager VPN

NetworkManager VPN on the Eitr bar. Place the NetworkManager VPN icon from
**Control Center > Plugins** (it joins the right-side icon group). The shield icon is
bright while a VPN profile is connected and dimmed while disconnected, using iwd or
unavailable. The reviewed manifest installs official `networkmanager-openvpn` and
`networkmanager-openconnect`.

## Panel

Click the bar icon for the panel:

- **Heading**: connection state and **Import** (or **Open Settings** when the desktop
  uses iwd).
- **Active profile**: the connected profile's name, protocol (`OpenVPN`, `OpenConnect`
  or `WireGuard`), interface, IP address (with a copy button), gateway/server and DNS.
- **Profiles**: every OpenVPN, OpenConnect and WireGuard profile known to
  NetworkManager, with a connect/disconnect switch.
- **When using iwd**: explains that NetworkManager VPN profiles need the NetworkManager
  backend and opens **Settings > Connections > Wi-Fi > WiFi backend** instead of failing.

Status comes from `status.py --json` (`nmcli` connection list and non-secret profile
details, three-second deadlines, at most 100 profiles). The bar icon refreshes every
15 seconds while placed; the open panel every 5 seconds, with no background polling
while nothing shows them.

## Actions

The panel runs `action.py` detached with fixed argv. Connecting and disconnecting a
profile select it by UUID (`nmcli --wait 30 connection up/down uuid <UUID>`), so
duplicate names and names containing colons stay unambiguous, and NetworkManager's
desktop authentication popup handles any provider credentials without asking for
passwords in the bar.

Import accepts a full `.ovpn` or `.conf` path in Eitr's task terminal, reviews it before
`nmcli` imports it, and disables autoconnect.

## Walker rows

Import an OpenVPN profile, Connect a VPN profile, Disconnect a VPN profile, and Status.
On iwd, every row explains the NetworkManager backend choice and opens the Settings
page for it.
