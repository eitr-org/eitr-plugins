# Ollama

A management panel for **Ollama (local, experimental)** in Eitr. It uses Eitr's
`eitr-ollama.service`, model store and loopback API. It never installs Ollama,
creates a competing server, or changes the default assistant.

## Panel and bar

- Start or stop the existing **user** service. Without a complete core setup, one
  explanation and **Set up** open Walker's existing Default Assistant chooser.
  Core readiness comes from `ai-assistant.py local-state`. Select Ollama there; core setup owns confirmation, package installation,
  service creation and the first model download. A partial setup can be repaired there too.
- Loaded models show memory use. When `/api/ps` includes `size_vram`, the row
  separates VRAM from RAM (`size - size_vram`); otherwise it explicitly says the
  split is unavailable. **Unload** sends an empty generation with `keep_alive: 0`.
- Installed models show size and the API's modification date. **Delete** opens
  an inline confirmation. Deleting `qwen3:4b` also warns that local chat will
  require setup again. Deletion and service stop are disabled during a download.
- Download a library model by name, or select a suggestion. Progress shows
  the current streamed layer's completed/total bytes. Preparation and verification
  have no byte percentage. **Cancel** stops only this plugin's download helper.
  Interrupted/failed downloads can be retried; Ollama handles cached layers.
- **Open Chat** runs exactly the SUPER + A entry point:
  `python3 /usr/share/eitr/walker/scripts/actions/ai-assistant.py open`.
  This opens whichever assistant the user selected as default.
- The chip's dot shows a loaded model or an active download. The bar item sets
  `api.detail` to the loaded model names and active download, without repeating
  the plugin name. Eitr's single tooltip shows **Ollama · <detail>**, or just
  **Ollama** when idle. Click, Enter and Space open the panel through the host.

Eitr currently fixes its local model to `qwen3:4b`. The plugin displays that
choice; there is no supported model chooser to call. Downloading another model
does not change the core assistant's model.

## Downloads and refresh

All HTTP connections are made directly to `127.0.0.1:11434`, ignoring proxies,
`OLLAMA_HOST` and redirects. Normal requests have a 2.5-second deadline and
1 MiB response cap. Inventories over 100 models or a 60 KiB snapshot return
an explicit error instead of silently dropping rows or exceeding the host’s 64 KiB cap. The streamed pull has a 30-second idle timeout, a 24-hour
absolute deadline and 16 KiB progress-line cap. Registry-address names and cloud
model tags are refused; only local library downloads are offered.

A pull is a transient systemd user unit, `eitr-ollama-plugin-pull.service`, with
`RuntimeMaxSec=86400` and `TimeoutStopSec=5`. It is separate from the panel and
bar, so closing either does not cancel it. A file lock prevents duplicate workers.
SIGTERM closes the HTTP stream and saves cancellation; if killed abruptly, the
next snapshot identifies the inactive unit as interrupted. Cancellation does not
stop another client's independent pull of the same model.

Atomic progress lives in `$XDG_STATE_HOME/eitr/ollama-plugin/pull.json` (0600;
default `~/.local/state/eitr/ollama-plugin`). The directory also holds the worker
lock. Progress writes are limited to four per second, plus the final state.
There is no persistent plugin service, login hook or background status loop.
The bar refreshes every **30 seconds**, fetching only `/api/ps`; the open panel
refreshes every **2 seconds**, also fetching `/api/tags`. Both skip HTTP when
Eitr's service is stopped or absent. The bar dot can lag by up to 30 seconds.
The host's `api.observed` gates post-action refresh in the panel.

The plugin uses `api.controls` for buttons, the model field and suggestions,
and ships German, Spanish, French, Japanese, Korean, Brazilian Portuguese and
Simplified Chinese interface text with an English fallback. No core files change.

## Checks and limits

`bash tools/check.sh` runs fake-service/API tests and isolated offscreen renders
using the sibling Eitr checkout's real controls. It neither contacts Ollama nor
changes the user's configuration or services. Render PNGs go into the task
folder (override with `EITR_OLLAMA_RENDERS`). A real systemd/Ollama/GPU download
and cancellation remain to be checked on an authorized test installation.
Removing the plugin does not stop an already detached download; cancel it first,
or stop `eitr-ollama-plugin-pull.service`. The unit expires after 24 hours.

API shapes follow [Ollama's API reference](https://github.com/ollama/ollama/blob/main/docs/api.md).
Approximate suggestions, checked November 16, 2026:
[qwen3:4b, 2.5 GB](https://ollama.com/library/qwen3:4b),
[llama3.2:3b, 2.0 GB](https://ollama.com/library/llama3.2:3b),
[gemma3:1b, 806 MB](https://ollama.com/library/gemma3:1b).
Sizes and licenses depend on the selected tag; consult the model's library page.
