"""The desktop portal's file chooser (xdg-desktop-portal-gtk on Eitr), as Eitr's Settings uses it."""
import os
from pathlib import Path

PORTAL = 'org.freedesktop.portal.Desktop'
PORTAL_PATH = '/org/freedesktop/portal/desktop'
CALL_TIMEOUT = 5000


def choose_files(title):
    """Wait for the person to pick files or cancel; returns local paths, empty when cancelled."""
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio, GLib
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    token = f'eitr_phone_link_{os.getpid()}'
    sender = bus.get_unique_name().lstrip(':').replace('.', '_')
    expected = f'{PORTAL_PATH}/request/{sender}/{token}'
    loop = GLib.MainLoop()
    outcome = {}
    timer_active = False

    def responded(_connection, _sender, _path, _interface, _signal, parameters):
        code, results = parameters.unpack()
        outcome.update(code=code, uris=list(results.get('uris', [])))
        loop.quit()

    def listen(handle):
        return bus.signal_subscribe(PORTAL, 'org.freedesktop.portal.Request', 'Response', handle,
                                    None, Gio.DBusSignalFlags.NONE, responded)

    subscription = listen(expected)
    options = {
        'handle_token': GLib.Variant('s', token),
        'modal': GLib.Variant('b', True),
        'multiple': GLib.Variant('b', True),
        'current_folder': GLib.Variant('ay', os.fsencode(str(Path.home())) + b'\0'),
    }
    try:
        handle = bus.call_sync(PORTAL, PORTAL_PATH, 'org.freedesktop.portal.FileChooser', 'OpenFile',
                               GLib.Variant('(ssa{sv})', ('', title, options)), GLib.VariantType.new('(o)'),
                               Gio.DBusCallFlags.NONE, CALL_TIMEOUT, None).unpack()[0]
        if handle != expected:
            bus.signal_unsubscribe(subscription)
            subscription = listen(handle)

        def expired():
            nonlocal timer_active
            timer_active = False
            outcome['code'] = 1
            try:
                bus.call_sync(PORTAL, handle, 'org.freedesktop.portal.Request', 'Close', None, None,
                              Gio.DBusCallFlags.NONE, CALL_TIMEOUT, None)
            except GLib.Error:
                pass
            finally:
                loop.quit()
            return GLib.SOURCE_REMOVE

        deadline = GLib.timeout_add_seconds(120, expired)
        timer_active = True
        try:
            if 'code' not in outcome:
                loop.run()
        finally:
            if timer_active:
                GLib.source_remove(deadline)
    finally:
        bus.signal_unsubscribe(subscription)
    if outcome.get('code') != 0:
        return []
    paths = [Gio.File.new_for_uri(uri).get_path() for uri in outcome.get('uris', [])]
    if any(not path for path in paths):
        raise ValueError('Choose files stored on this computer.')
    return [Path(path) for path in paths]
