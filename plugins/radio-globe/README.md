# Radio Globe

Explore live radio on an orthographic globe, search for stations, save favorites
and listen through mpv. The manifest requests the official Arch `mpv` and `python-gobject`
packages. `media.py` puts the playing station in the desktop's media controls as a live
stream: Stop only, no pause, seeking or length, and the song the station announces as the
title with the station as the artist. Volume is Eitr's own, where the stream is named Radio Globe. Installation uses Eitr's normal package review; the plugin does not
install packages or start a login service itself.

## Controls

- Click the bar's globe to open the panel. Its activity dot identifies this
  plugin's player. It publishes `Now playing · <station>` through `api.detail`,
  which Eitr appends to the plugin title in its native bar tooltip; stopping
  clears the detail. The local status refresh is every 30 seconds,
  with another refresh on hover.
- Drag the globe to rotate and scroll to zoom up to 4× towards the pointer. Countries
  show with their borders; hovering a country or its dot lightens it and names it with
  its station count, and clicking loads its stations and fills it in the accent.
- Search globally by **name** or **tag**, or by **country**: the filter button at the end
  of the search field opens a small menu to choose. By country, typing lists the matching
  countries (Enter takes the first), the way to reach small ones. Empty search returns to
  the chosen country. Results arrive in pages of 50; **Previous** and **Next** change pages.
- **Favorites**, beside the search field, shows saved stations, including when offline;
  the back arrow beside its heading (or Escape, or the button again) returns to the list.
- Click a station name to play: the globe turns to the station's own location when
  Radio Browser lists one, else to its country. Its star saves or removes a favorite.
  Search filters favorites locally.
- **Stop** is in the desktop's media controls (the bar and the Media panel). Closing the panel keeps audio playing.
  Reopening it restores current local player state. Adjust the **Radio Globe**
  stream in Eitr's Volume panel.

The globe spins slowly until the first drag, click or scroll, and pauses while
hovered. Reduce motion disables the spin. Eitr does not expose its motion
preference in the plugin API, so this plugin watches the existing
`$XDG_CONFIG_HOME/quickshell/desktop-bar/bar-settings.json` read-only while the
panel is open; a missing or invalid file disables motion. Nothing writes that
file. All interactive controls come from `api.controls`; colors follow the
theme's palette. UI text includes de, es, fr, ja, ko, pt_BR and zh_CN.

## Data and offline behavior

Radio Browser server discovery follows its [documented DNS server
list](https://api.radio-browser.info/): resolve `all.api.radio-browser.info`,
reverse-resolve the resulting addresses, shuffle the HTTPS mirror names and try
another mirror on failure. Requests send `User-Agent: EitrRadioGlobe/1.0` with no
personal information. DNS and the whole API operation have a seven-second
deadline; individual HTTP reads time out after two seconds. Every helper command
has an outer nine-second deadline, including file locks and local player IPC.

Countries come from `/json/countries?hidebroken=true`; country stations use
`/json/stations/bycountrycodeexact`, and name/tag searches use
`/json/stations/search`. Both server and client filter broken stations. The
client requires `lastcheckok == 1` and an HTTP or HTTPS stream, preferring
`url_resolved`; it never executes station text or loads station favicons.
Country dots scale logarithmically with the reported station count. The country
cache lasts 24 hours; expired data remains usable with an explicit offline
message if refresh fails. **Retry** appears only after country or station loading
fails (including a stale-cache fallback), and disappears when loading is retried
or succeeds. Playback errors do not show this loading action. Without a cache,
failure shows a connection message. An API outage does not stop an already
playing stream.

## Local files and playback

- `$XDG_CONFIG_HOME/eitr/plugins/radio-globe/settings.json`: favorites keyed by
  station UUID. Writes are locked, private and atomic; at most
  200 favorites are retained.
- `$XDG_CACHE_HOME/eitr/plugins/radio-globe/countries.json`: the one-day cache.
- `$XDG_RUNTIME_DIR/eitr/plugins/radio-globe/`: private mpv socket and current
  station metadata. Stop sends `quit` only to that socket. Replacing a station
  stops the previous instance before launching another. No global process names
  or remembered PIDs are signalled.

Config and cache paths fall back to `~/.config` and `~/.cache`. Playback requires
`XDG_RUNTIME_DIR`. mpv disables user configuration, scripts, video and yt-dlp,
receives the stream as one argument after `--`, and has an eight-second network
timeout. Playback ends when the stream ends. The plugin reports local playback
state while the panel is open; it performs no station/API polling while closed.
Lofi Radio's interactive lowfi terminal cannot play an arbitrary station, so
this plugin uses the brief's mpv fallback. mpv starts at `--volume=100` with
`--audio-client-name=Radio Globe` so Eitr's per-application slider controls volume.

## Privacy

**Station lists come from Radio Browser; streams come from each station.**
Radio Browser receives your IP address and country/name/tag requests. A chosen
station and its streaming/CDN providers receive your IP address and stream
requests. HTTP streams are unencrypted. Favorites stay on this computer; the
plugin sends no personal identifiers, analytics, votes or click-tracking calls.
The country shapes and marker locations are bundled and need no map service.

## Map sources and licenses

Made with [Natural Earth](https://www.naturalearthdata.com/). `data/shapes.json`
holds the country shapes of **1:110m Admin 0 – Countries**, simplified to 0.25 degrees
(about 58 KiB); zoomed in past 1.5×, the globe draws `data/shapes-detail.json`, from
**1:50m Admin 0 – Countries** simplified to 0.12 degrees (about 172 KiB), read the
first time you zoom in. Both are geometry only, rounded to 0.1 degrees, keyed by ISO
code (areas without one under `-`, drawn but not selectable). Import the
[110m](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson)
and [50m](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson)
GeoJSON with `tools/radio-globe/build-map.py --countries-coarse … --countries …`.
Natural Earth data is [public domain](https://www.naturalearthdata.com/about/terms-of-use/).
The repository's MIT license covers the plugin code, not a claim of ownership
over these public-domain coordinates.

`data/countries.json` holds 250 marker positions: Natural Earth's label point for
each country in **1:50m Admin 0 – Countries** (a spot chosen to sit well inside it;
where several features share a code, the one with the most land), and for the few
small territories that file does not list, the mean of their time zone locations
from the public-domain [IANA timezone database](https://data.iana.org/time-zones/tz-link.html)
`zone.tab`. Import the [upstream GeoJSON](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson)
with `build-map.py --countries`. They are display locations, not country boundaries.
Countries without a marker remain reachable through **By country**.
Small islands and some coastline detail are intentionally omitted at these scales.

## Verification and host limitations

Run `bash tools/check.sh` for offline helper and QML render tests. Run
`python3 tools/radio-globe/render.py --output /tmp/radio-globe-previews` for
dark/light panel and bar previews with fake stations and isolated XDG paths.
No network, audio, desktop services or live configuration is changed by those
fixtures. `tools/radio-globe/build-map.py --check` validates bundled geometry
and checks that every country in the local IANA `zone.tab` has a marker.

The current host limits a panel viewport to 360 px high; it supplies scrolling
when this content needs more room. The shared button's text mode is used for
compact glyph actions to avoid a binding-loop warning in its icon mode.
The plugin uses Eitr's native `title · detail` bar tooltip and supplies no bar
tooltip of its own. Older hosts that ignore `api.detail` show just the title.
Live radio availability,
real mpv audio and tooltip placement on each bar edge need an installed-session
check; the offline fixture verifies rendering and client behavior only.
