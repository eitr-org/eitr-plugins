# Visualizer

A desktop audio visualizer for [Eitr](https://github.com/eitr-org/eitr). It moves
with whatever is playing on your computer and follows your theme colours.

## Styles

- **Wave** (default): a smooth glowing wave, low tones in the centre mirrored
  outward, with soft afterimages and a reflection fading below it. When nothing
  plays it relaxes into a low line.
- **Terminal**: classic spectrum bars from low to high tones, with a gradient in
  your theme's accent colour.

Right-click the widget (or use Control Center > Plugins) to switch styles; Eitr
shows them next to its own size, background and layer options. The choice is
saved in `~/.config/eitr-plugin-visualizer/options.json`. The widget has a
transparent background by default.

## Install

1. In Walker, open **Install > Plugins > Add Plugin…** and paste
   `https://github.com/eitr-org/eitr-plugins` and pick **Visualizer**. Review it and confirm.
2. Open **Control Center > General > Plugins > Manage**, add **Visualizer** and
   choose a monitor.
3. Use **Edit position** to move and resize it (drag it to the full screen
   width if you like), then **Done**.
4. Optional: turn on **Show above windows** to keep it visible over your apps.
   It then lets clicks pass through; switch it back behind windows to right-click
   it.

Requires Eitr with plugin schema version 2 and the `audio-spectrum` capability.

## Privacy

Visualizer only reads spectrum levels that Eitr provides. It records, stores and
sends no audio, runs no commands and uses no network.

## License

MIT
