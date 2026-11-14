# World clock

Offline city times using Python's system IANA zoneinfo database, including daylight saving.
Enable its bar item from Control Center > Plugins. Open **Control Center > General >
Plugins > World clock** to add your first city; until then the bar shows a globe that opens this panel.
Search cities, states/provinces, countries or IANA zones (Porto, São Paulo / sao paulo,
California, Brazil, Tokyo, Europe/Lisbon). Search ignores accents and case; prefix
matches precede substring matches, then larger populations come first. At most 30
results show a country flag, name and location. Matching states/provinces appear before cities; countries filter results but are not choices. States use the time zone of their most populous city in the bundled dataset, even when they span several zones. The secondary line names that city (for example, “State · United States · Los Angeles time”). State labels default to the first three letters uppercased (California → CAL), and remain editable. Coverage follows GeoNames
cities15000, rather than every village. Exact IANA zone names remain searchable.
City choices retain the city name and ISO country code with their zone and editable
three-character default label. Flags appear in the saved list and before bar labels.
Old zone-and-label preferences remain valid and show no inferred flag.

The first 1–10 saved choices appear immediately before the clock, in the bar's 12/24-hour
format. The panel shows every chosen city, Yesterday/Today/Tomorrow relative to this
computer, and its current UTC-offset difference. Edit a short label, reorder with arrows,
remove a choice, or select 1–10 bar clocks from the dropdown. Up to 24 choices are supported. The same zone may be saved for different names, such as California and Los Angeles; an already saved zone/name pair is disabled in search.
Preferences are atomic JSON in `$XDG_CONFIG_HOME/eitr/plugins/world-clock.json`
(default `~/.config/eitr/plugins/world-clock.json`).

Streams emit once on opening, at minute boundaries, and within approximately one second of settings changes, including deleting every choice (which restores the globe). While waiting, a cheap stat checks the settings inode, nanosecond mtime and size. Compact clock rows with stable zone/name identity keys fit Eitr’s 4 KiB line limit; full metadata stays in the status command and is refreshed by panels when new named rows arrive.
Search is debounced and runs through an argv-based runtime data command, not in QML.
The compressed catalog and normalized index are cached once per Python process. A successful
edit refreshes the panel immediately; the bar and other open hosts receive the changed stream within approximately one second.
No network, packages, credentials, background service or privileged actions.
Invalid saved preferences produce a visible error rather than being overwritten.

Requires Eitr's clock bar-slot support. The first two placed clock-slot plugins use
that slot; further entries use the status group. Drop hides clock-slot items.
English only: plugins have no independent translation catalog (the Tailscale plugin
uses keys from the desktop catalog).


The host caps the bar item at 320 logical pixels; the plugin adds no separate width cap. Compact flag/label/time text is elided on the right. Selecting 10 includes the first ten choices in the text, but all ten will generally not fit in 320 pixels; open the panel to see every clock. Country flags use Unicode regional indicators and the system
emoji font. City metadata is bounded to 200 printable characters and a known country
code; unknown settings fields are refused.

GeoNames data © GeoNames contributors, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
from [GeoNames](https://www.geonames.org/). The bundled dataset is a reduced and
compressed adaptation; see [data/LICENSE](data/LICENSE). To rebuild offline from
local GeoNames downloads:

```sh
python3 tools/build_world_clock_data.py /path/to/geonames plugins/world-clock/data/cities.json.gz
```

Run repository checks with `bash tools/check.sh`; when the host checkout is not the
sibling `../eitr`, set `PYTHONPATH=/path/to/eitr/distro/lib`. Render fixtures use
Quickshell's offscreen platform and temporary configuration directories.
