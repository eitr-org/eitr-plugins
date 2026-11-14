# World clock

Offline city times using Python's system IANA zoneinfo database, including daylight saving.
Enable its bar item from Control Center > Plugins. Open **Control Center > General >
Plugins > World clock** to add your first city; until then the bar shows a globe that opens this panel.
Search cities, states/provinces, countries or IANA zones (Porto, São Paulo / sao paulo,
California, Brazil, Tokyo, Europe/Lisbon). Search ignores accents and case; prefix
matches precede substring matches, then larger populations come first. At most 30
results show a country flag, city and State, Country. Coverage follows GeoNames
cities15000, rather than every village. Exact IANA zone names remain searchable.
City choices retain the city name and ISO country code with their zone and editable
three-character default label. Flags appear in the saved list and before bar labels.
Old zone-and-label preferences remain valid and show no inferred flag.

The first one or two cities appear immediately before the clock, in the bar's 12/24-hour
format. The panel shows every chosen city, Yesterday/Today/Tomorrow relative to this
computer, and its current UTC-offset difference. Edit a short label, reorder with arrows,
remove a city, or choose one/two bar cities. Up to 24 distinct zones are supported.
Preferences are atomic JSON in `$XDG_CONFIG_HOME/eitr/plugins/world-clock.json`
(default `~/.config/eitr/plugins/world-clock.json`).

Streams emit once on opening, then once per minute at the minute boundary. Compact
clock rows fit Eitr’s 4 KiB line limit; full city metadata stays in the status command.
Search is debounced and runs through an argv-based runtime data command, not in QML.
The compressed catalog and normalized index are cached once per Python process. A successful
edit refreshes the panel immediately; the bar and other open hosts see it at the next minute.
No network, packages, credentials, background service or privileged actions.
Invalid saved preferences produce a visible error rather than being overwritten.

Requires Eitr's clock bar-slot support. The first two placed clock-slot plugins use
that slot; further entries use the status group. Drop hides clock-slot items.
English only: plugins have no independent translation catalog (the Tailscale plugin
uses keys from the desktop catalog).


The bar is capped at 360 logical pixels and elides long content. The existing limit
of one saved city per zone remains; another city in that zone is disabled until the
saved one is removed. Country flags use Unicode regional indicators and the system
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
