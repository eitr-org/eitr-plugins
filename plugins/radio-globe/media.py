"""The playing station in the desktop's media controls (MPRIS), while Radio Globe's mpv runs.

A radio stream is live: it can neither pause nor seek and has no length, so this says so and
offers Stop alone; a generic mpv bridge would claim a seekable track whose length is only the
buffer. The title is the song the station announces (its ICY title) when it sends one, with
the station's name as the artist. Runs beside mpv and exits when mpv's socket closes.

Usage: media.py SOCKET STATION_NAME
"""
import json
import os
import socket
import sys
import threading

from gi.repository import Gio, GLib

ROOT = '''
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/><method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/><method name="Previous"/><method name="Pause"/>
    <method name="PlayPause"/><method name="Stop"/><method name="Play"/>
    <method name="Seek"><arg name="Offset" type="x" direction="in"/></method>
    <method name="SetPosition"><arg name="TrackId" type="o" direction="in"/><arg name="Position" type="x" direction="in"/></method>
    <method name="OpenUri"><arg name="Uri" type="s" direction="in"/></method>
    <signal name="Seeked"><arg name="Position" type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="Rate" type="d" access="read"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>'''
PLAYER = 'org.mpris.MediaPlayer2.Player'


def metadata(station, song):
    """MPRIS metadata: the announced song as title and the station as artist, or the station alone."""
    values = {'mpris:trackid': GLib.Variant('o', '/org/eitr/RadioGlobe/Track')}
    if song:
        values['xesam:title'] = GLib.Variant('s', song)
        values['xesam:artist'] = GLib.Variant('as', [station])
    else:
        values['xesam:title'] = GLib.Variant('s', station)
    return values


def properties(station, song):
    fixed = dict(CanQuit=False, CanRaise=False, HasTrackList=False, Identity='Radio Globe',
                 SupportedUriSchemes=[], SupportedMimeTypes=[], PlaybackStatus='Playing', Rate=1.0,
                 Position=0, MinimumRate=1.0, MaximumRate=1.0, CanGoNext=False, CanGoPrevious=False,
                 CanPlay=False, CanPause=False, CanSeek=False, CanControl=True)
    kinds = dict(SupportedUriSchemes='as', SupportedMimeTypes='as', Identity='s', PlaybackStatus='s',
                 Rate='d', MinimumRate='d', MaximumRate='d', Position='x')
    values = {name: GLib.Variant(kinds.get(name, 'b'), value) for name, value in fixed.items()}
    values['Metadata'] = GLib.Variant('a{sv}', metadata(station, song))
    return values


def song_title(value):
    """The station's announced title, cleaned; '' when it sends none."""
    return ' '.join(value.split())[:200] if isinstance(value, str) else ''


class Bridge:
    def __init__(self, path, station):
        self.path, self.station, self.song = path, station, ''
        self.loop = GLib.MainLoop()
        self.connection = None
        self.info = Gio.DBusNodeInfo.new_for_xml(ROOT)

    def mpv(self, command):
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(0.5)
            connection.connect(self.path)
            connection.sendall((json.dumps({'command': command}) + '\n').encode())

    def call(self, connection, sender, path, interface, method, parameters, invocation):
        if interface == PLAYER and method == 'Stop':
            try:
                self.mpv(['quit'])
            except OSError:
                pass
        invocation.return_value(None)

    def get(self, connection, sender, path, interface, name):
        return properties(self.station, self.song).get(name)

    def acquired(self, connection, name):
        self.connection = connection
        for interface in self.info.interfaces:
            connection.register_object('/org/mpris/MediaPlayer2', interface, self.call, self.get, None)

    def announce(self, song):
        self.song = song
        if self.connection is None:
            return
        changed = GLib.Variant('(sa{sv}as)', (PLAYER, {'Metadata': properties(self.station, song)['Metadata']}, []))
        self.connection.emit_signal(None, '/org/mpris/MediaPlayer2', 'org.freedesktop.DBus.Properties',
                                    'PropertiesChanged', changed)

    def watch(self):
        """Follows mpv's ICY title until mpv closes its socket, then ends the bridge."""
        try:
            with socket.socket(socket.AF_UNIX) as connection:
                connection.connect(self.path)
                connection.sendall(b'{"command": ["observe_property", 1, "metadata/by-key/icy-title"]}\n')
                pending = b''
                while True:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    pending += chunk
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        if event.get('event') == 'property-change' and event.get('id') == 1:
                            GLib.idle_add(self.announce, song_title(event.get('data')))
        except OSError:
            pass
        GLib.idle_add(self.loop.quit)

    def run(self):
        name = 'org.mpris.MediaPlayer2.radio_globe.instance' + str(os.getpid())
        owner = Gio.bus_own_name(Gio.BusType.SESSION, name, Gio.BusNameOwnerFlags.NONE,
                                 self.acquired, None, lambda connection, lost: self.loop.quit())
        threading.Thread(target=self.watch, daemon=True).start()
        self.loop.run()
        Gio.bus_unown_name(owner)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: media.py SOCKET STATION_NAME')
    Bridge(sys.argv[1], sys.argv[2][:200] or 'Radio Globe').run()
