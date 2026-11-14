# World clock

Offline city times using Python's system IANA zoneinfo database, including daylight saving.
Enable its bar item from Control Center > Plugins. Open **Control Center > General >
Plugins > World clock** to add your first city; the bar stays empty until a city is selected. Search a city represented in IANA
(for example Lisbon) or a full zone such as Europe/Lisbon. Zoneinfo is a timezone
catalog, not a database of every town; nearby towns sharing a zone use that zone and
an editable label.

The first one or two cities appear immediately before the clock, in the bar's 12/24-hour
format. The panel shows every chosen city, Yesterday/Today/Tomorrow relative to this
computer, and its current UTC-offset difference. Edit a short label, reorder with arrows,
remove a city, or choose one/two bar cities. Up to 24 distinct zones are supported.
Preferences are atomic JSON in `$XDG_CONFIG_HOME/eitr/plugins/world-clock.json`
(default `~/.config/eitr/plugins/world-clock.json`).

Streams emit once on opening, then once per minute at the minute boundary. Compact
clock rows fit Eitr’s 4 KiB line limit; the panel loads the offline search catalog
separately once when it opens. A successful
edit refreshes the panel immediately; the bar and other open hosts see it at the next minute.
No network, packages, credentials, background service or privileged actions.
Invalid saved preferences produce a visible error rather than being overwritten.

Requires Eitr's clock bar-slot support. The first two placed clock-slot plugins use
that slot; further entries use the status group. Drop hides clock-slot items.
English only: plugins have no independent translation catalog (the Tailscale plugin
uses keys from the desktop catalog).
