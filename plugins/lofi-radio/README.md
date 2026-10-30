# Lofi Radio

Plays lofi music using [lowfi](https://github.com/talwat/lowfi). Install the
`lowfi` AUR package yourself: **Walker > Install > Packages > Yay (AUR)**, search
`lowfi`, review its build files and confirm. This plugin never installs packages;
without lowfi both rows say how to get it.

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
