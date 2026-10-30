# Lofi Radio

Plays lofi music using [lowfi](https://github.com/talwat/lowfi), an AUR package
(also in **Walker > Install > Packages > Yay (AUR)**). Without lowfi, both rows open
Eitr's install screen (`eitr package install --aur lowfi`): it explains that AUR
packages come from the community, offers the build file, and installs only when
you press Enter. The plugin never installs anything by itself.

## Actions

- **Start / stop radio** starts lowfi in a Kitty terminal that waits out of sight
  in a scratchpad workspace, or stops the player this plugin started. Other lowfi
  sessions are left alone.
- **Open player** shows or hides that terminal (it starts the radio if stopped).

The AUR package is built with all features, including MPRIS, so the desktop
bar's media widget and the media keys play, pause and skip it. In the player:
Space or `p` pauses, `s` skips, up/down change the volume, `q` quits.

There are no services, login hooks or automatic playback. The runtime lock and
the player's PID and start time live in `$XDG_RUNTIME_DIR/eitr-lofi-radio`;
stopping uses a pidfd, so a reused PID is never signalled.

Checked on Eitr 0.7 (Hyprland 0.57) with lowfi 2.0.7: start, the bar's media
controls, Open player twice, stop.
