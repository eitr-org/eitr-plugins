# Hardware

Desktop widget showing live CPU, GPU, RAM, root storage and network throughput
from Eitr's existing hardware broker (`api.hardware` via the `hardware`
capability), without running a second background reader.

## Layout

- **Detailed** (default): Shows CPU, GPU (hidden automatically when unavailable),
  RAM, root Storage, optional temperatures, model/capacity details and Network
  Download/Upload speeds.
- **Compact**: Single-row summary bar matching Eitr's System Monitor wording, or
  wraps cleanly at narrow widths (`minWidth: 260`).

Right-click the widget to switch between **Detailed** and **Compact**; each
placed copy remembers its chosen layout in per-instance widget storage.

## Capabilities & Language

- Requires schema version 2 capability `hardware` (approved during installation
  review; reads only while the widget is placed and visible).
- Widget UI strings are English only (`eitr-plugins` does not ship an independent
  translation catalog).
