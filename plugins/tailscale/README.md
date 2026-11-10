# Tailscale

Tailscale on the Eitr bar. Place the Tailscale icon from **Control Center > Plugins**
(it joins the right-side icon group). The icon is bright while connected and dimmed,
with a crossed-out network, while disconnected, signed out or unavailable.

## Panel

Click the icon for the panel:

- **Heading**: the connection switch, or the first step that is missing:
  **Set up** (Tailscale not installed or its service not answering) or **Sign in**.
- **Allow**: shown when this account is not Tailscale's operator yet; it explains and
  runs `sudo tailscale set --operator=$USER` in a terminal after confirmation.
- **This computer**: device name, Tailscale IP (with a copy button) and tailnet name.
- **Devices**: every peer, online first, with its address and whether the path is
  direct, relayed or idle. Each has a copy-address button; your own online devices
  also have **Send files**, which opens the desktop's file chooser (the portal Eitr's
  Settings uses) and sends the chosen files with `tailscale file cp`.
- **Open folder**: opens `~/Documents/Taildrop`.

Status comes from `status.py --json` (`tailscale status --json` plus the operator
preference, three-second deadlines, at most 200 peers). The bar icon refreshes every
15 seconds while placed; the open panel every 5 seconds, and a few extra times right
after Connect or Disconnect.

## Actions

The panel runs `action.py` detached with fixed argv. Connect, Disconnect, Send files
and Open folder run without a terminal and report failures as notifications. A step
that needs a password or the browser (Sign in, Allow, Set up) opens Eitr's task
terminal. Set up runs Eitr's reviewed Remote Access setup
(`remote-access.py away setup`, which installs Tailscale and uses the root-owned
`eitr-system` helper); the plugin has no root helper of its own.

## Receiving files

The plugin's user service (`receive.py`) waits for Taildrop files and moves them into
`~/Documents/Taildrop`, then shows a notification naming them. Taildrop only accepts
files from devices signed in to your own account. Same-named files get a numbered
name; nothing is overwritten. While Tailscale is missing, stopped or this account
is not its operator, the service retries with back-off (5 seconds to 5 minutes).
Notifications include file names, so they appear in notification history.

## Walker rows

Connect, Disconnect, Sign in, Send files (typed paths, reviewed by the Eitr wizard,
own online devices only), Receive waiting files, and Allow this account to control
Tailscale.

"Tailscale" and the Tailscale logo are trademarks of Tailscale Inc. This plugin is
not made or endorsed by Tailscale; the logo only identifies the service it controls.
