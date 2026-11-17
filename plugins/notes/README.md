# Notes

Desktop sticky notes for [Eitr](https://github.com/eitr-org/eitr). Each placed widget is an independent plain-text note saved per copy.

## Features

- **Click and type:** plain text with line breaks, word wrapping and scrolling when long. Changes are debounced and saved automatically per widget copy in `$XDG_DATA_HOME/eitr/plugin-data/notes/note/<instance>.json`, surviving logins, restarts and plugin updates.
- **Colors:** right-click the note (or open **Control Center > Plugins**) to pick from five soft note colors (**Yellow**, **Green**, **Blue**, **Pink**, **Purple**) adapted for light and dark themes, or **Theme** to follow your desktop panel surface.
- **New note:** Eitr does not expose a separate duplicate API to plugin QML, so use **Duplicate** in the note's right-click menu or **Control Center > Plugins** (or **Add another copy**) to place another independent note.
- **Move and resize:** use **Edit position** from the right-click menu or **Control Center > Plugins**.
- **Keyboard focus:** behind-windows notes request on-demand layer-shell keyboard focus while editing and release it on **Escape** or clicking elsewhere.

## Install

1. In **Eitr Store > Plugins** (or Walker **Install > Plugins > Add Plugin…**), open `https://github.com/eitr-org/eitr-plugins` and select **Notes**.
2. Open **Control Center > Plugins > Notes** and add a note to a display.

Requires Eitr with plugin schema version 2, per-instance widget storage and on-demand widget keyboard focus.

English only: plugins have no independent translation catalog.

## Privacy

Note contents are saved locally per widget instance and are never logged or sent anywhere.

## License

MIT
