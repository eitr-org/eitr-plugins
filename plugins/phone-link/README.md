# Phone Link

Connect Android phones and iPhones to Eitr through KDE Connect. Install the
KDE Connect app on the phone, open it, and join the same trusted local network
as the computer. Approve the plugin's official Arch dependencies (`kdeconnect`
and `python-gobject`) in Eitr's normal package review.

True AirDrop is out of scope. This plugin uses KDE Connect and does not discover
AirDrop peers or implement Apple's wireless protocol.

## Panel and bar

Click the phone icon on the bar to open the panel. If you removed its placement,
add it again from **Control Center > Plugins**. The icon is dimmed when no paired
device is reachable. It sets `api.detail` to the first connected device's name
and battery when known, for example **Phone · 80%**. Eitr supplies the themed
tooltip **Phone Link · Phone · 80%**, or **Phone Link · No phone connected**
when no paired device is reachable.

Each connected device has a card with its name, battery bar and percentage,
and charging state. Its five actions stay visible in equal tiles in a three-column,
two-row grid; the sixth slot is empty. **Unpair** is a quiet text action below the
tiles and requires a separate **Confirm unpair** step. Offline and available phones
appear as compact rows under **Other devices**, with **Pair** or **Unpair** as
appropriate. Incoming requests show **Accept / Reject** and the verification key
when KDE Connect provides it; compare the code on both devices. Outgoing requests
also keep their code visible while waiting.

The panel requests a 420 px width and a 640 px maximum content height before the
host scrolls. Headings, body text, captions and corner preference come from Eitr's
shared panel roles and controls, in both light and dark themes.

- **Send files** opens the desktop portal file chooser, with multiple selection.
  Cancellation sends nothing. Local file URIs preserve spaces and leading dashes.
- **Send clipboard** explicitly shares the current desktop clipboard as text.
  It uses the same D-Bus operation as `kdeconnect-cli --share-text`, keeping the
  text out of process arguments and logs. Empty or oversized text is refused.
- **Ring** asks the phone to ring through KDE Connect's Find My Phone.
- **Ping** sends a KDE Connect ping, not an ICMP network test.
- **Browse files** asks KDE Connect to mount the phone's shared SFTP storage and
  opens the mount in the default file manager. The phone must share storage and
  grant the relevant permissions. A failed mount opens nothing.

Unavailable tiles are dimmed according to the device's loaded plugins. Hover a
disabled tile for **Not shared by this phone**; the same explanation is available
to accessibility tools.
Android and iOS support different features and background behavior; this plugin
cannot add capabilities the phone app does not expose. Unknown batteries remain
unknown. Keep the phone app open if discovery is unreliable.

When KDE Connect is stopped, **Start KDE Connect** starts a recognized package-owned
user service if one exists. Otherwise it launches `kdeconnectd` detached with no
terminal. It does not create or enable a service. The reference package provides
`/usr/bin/kdeconnectd` and D-Bus activation, without a systemd user unit.

## Updates and privacy

`status.py --watch` subscribes to KDE Connect's D-Bus signals, including battery,
pairing, reachability, device changes and daemon ownership. It sends an initial
JSON snapshot, then coalesces events for 150 ms. There is no periodic polling.
Eitr starts a stream only while its component is observed and stops it when hidden
or unloaded. The bar and panel can each have a stream while visible.
`status.py --json` supplies initial/on-demand data; a completed action requests a
fresh snapshot. Status reads use `NO_AUTO_START`, so opening the panel never starts
the daemon without pressing Start.

Snapshots have a six-second total budget and at most one second per D-Bus call.
The host limits stream lines to 4096 bytes; the helper fits complete JSON into
4000 UTF-8 bytes and reads up to eight devices per snapshot, prioritizing incoming
requests and connected devices. A note appears if devices were omitted or failed
to answer. Open the KDE Connect application for the complete list in that case.

Actions recheck the selected phone rather than trusting a stale panel row. Most
commands have an eight-second deadline; file sharing has ten seconds. The portal
chooser can remain open for two minutes before cancellation. Action results show
in the panel. No clipboard content, device list or pairing key is written to disk.
The UI includes German, Spanish, French, Japanese, Korean, Brazilian Portuguese
and Simplified Chinese translations, selected using Qt's session locale.

KDE Connect already forwards supported phone notifications to Eitr's desktop
notification server, according to phone permissions and its notification settings.
This plugin does not implement another notification forwarder.

## Firewall

The reference Eitr tree ships nftables (`distro/system/firewall.nft`). It already
allows both of these rules in `table inet eitr_firewall`, `chain input`:

```nft
tcp dport 1714-1764 accept
udp dport 1714-1764 accept
```

The panel shows local-network setup guidance only when no device is connected.
The firewall note appears only during setup or when there are no devices. This
plugin never edits or reloads the firewall. If you maintain a different firewall,
allow TCP **and** UDP 1714–1764
from your trusted local network. Guest Wi-Fi/client isolation can still prevent
discovery even when the computer's firewall allows those ports.

## API considerations and verification

The supported plugin API exposes themed buttons and streams but no file picker,
so `portal.py` follows the existing Tailscale chooser adapter. No zenity, kdialog,
new desktop core code or persistent helper service is needed.

Bar tooltips require the Eitr host that displays the manifest title followed by
`api.detail`. The plugin supplies no tooltip popup of its own. Older hosts that
ignore bar-item detail display only **Phone Link**.

Run `bash tools/check.sh` in the repository. Backend tests mock commands and Gio;
the private-bus fixture uses `dbus-run-session` when local socket binding is allowed.
Offscreen tests load Eitr's real shared buttons with inert data in both themes,
including a Galaxy S23 Ultra at 44% on battery, pairing requests, unavailable
actions, multiple connected devices and unknown batteries.
They never contact the real session bus or perform a device action. Real Android
and iPhone pairing, file transfers, permissions and SFTP mounts still need hardware
verification.

The D-Bus contract follows KDE's upstream [device API](https://github.com/KDE/kdeconnect-kde/blob/master/core/device.h),
[battery plugin](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/battery/batteryplugin.h),
[SFTP plugin](https://github.com/KDE/kdeconnect-kde/blob/master/plugins/sftp/sftpplugin.h)
and [CLI](https://github.com/KDE/kdeconnect-kde/blob/master/cli/kdeconnect-cli.cpp).
