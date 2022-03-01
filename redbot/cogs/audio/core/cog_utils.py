from abc import ABC
from pathlib import Path
from typing import Final
from base64 import b64decode
from io import BytesIO
import struct

from redbot import VersionInfo
from redbot.core import commands
from redbot.core.i18n import Translator

from ..converters import get_lazy_converter, get_playlist_converter

__version__ = VersionInfo.from_json({"major": 2, "minor": 5, "micro": 0, "releaselevel": "final"})

__author__ = ["aikaterna", "Draper"]
_ = Translator("Audio", Path(__file__))

_SCHEMA_VERSION: Final[int] = 3
_OWNER_NOTIFICATION: Final[int] = 1

LazyGreedyConverter = get_lazy_converter("--")
PlaylistConverter = get_playlist_converter()
HUMANIZED_PERM = {
    "create_instant_invite": _("Create Instant Invite"),
    "kick_members": _("Kick Members"),
    "ban_members": _("Ban Members"),
    "administrator": _("Administrator"),
    "manage_channels": _("Manage Channels"),
    "manage_guild": _("Manage Server"),
    "add_reactions": _("Add Reactions"),
    "view_audit_log": _("View Audit Log"),
    "priority_speaker": _("Priority Speaker"),
    "stream": _("Go Live"),
    "read_messages": _("Read Text Channels & See Voice Channels"),
    "send_messages": _("Send Messages"),
    "send_tts_messages": _("Send TTS Messages"),
    "manage_messages": _("Manage Messages"),
    "embed_links": _("Embed Links"),
    "attach_files": _("Attach Files"),
    "read_message_history": _("Read Message History"),
    "mention_everyone": _("Mention @everyone, @here, and All Roles"),
    "external_emojis": _("Use External Emojis"),
    "view_guild_insights": _("View Server Insights"),
    "connect": _("Connect"),
    "speak": _("Speak"),
    "mute_members": _("Mute Members"),
    "deafen_members": _("Deafen Members"),
    "move_members": _("Move Members"),
    "use_voice_activation": _("Use Voice Activity"),
    "change_nickname": _("Change Nickname"),
    "manage_nicknames": _("Manage Nicknames"),
    "manage_roles": _("Manage Roles"),
    "manage_webhooks": _("Manage Webhooks"),
    "manage_emojis": _("Manage Emojis"),
}

DANGEROUS_COMMANDS = {
    "command_llsetup_java": _(
        "This command will change the executable path of Java, "
        "this is useful if you have multiple installations of Java and the default one is causing issues. "
        "Please don't change this unless you are certain that the Java version you are specifying is supported by Red. "
        "The default and supported version is currently Java 11."
    ),
    "command_llsetup_heapsize": _(
        "This command will change the maximum RAM allocation for the managed Lavalink node, "
        "usually you will never have to change this, "
        "before considering changing it please consult our support team."
    ),
    "command_llsetup_external": _(
        "This command will disable the managed Lavalink node, "
        "if you toggle this command you must specify an external Lavalink node to connect to, "
        "if you do not do so Audio will stop working."
    ),
    "command_llsetup_host": _(
        "This command is used to specify the IP which will be used by Red to connect to an external Lavalink node. "
    ),
    "command_llsetup_password": _(
        "This command is used to specify the authentication password used by Red to connect to an "
        "external Lavalink node."
    ),
    "command_llsetup_secured": _(
        "This command is used toggle between secured and unsecured connections to an external Lavalink node."
    ),
    "command_llsetup_wsport": _(
        "This command is used to specify the connection port used by Red to connect to an external Lavalink node."
    ),
    "command_llsetup_config_server_host": _(
        "This command specifies which network interface and IP the managed Lavalink node will bind to, "
        "by default this is 0.0.0.0 meaning it will bind to all interfaces, "
        "only change this if you want the managed Lavalink node to bind to a specific IP/interface."
    ),
    "command_llsetup_config_server_token": _(
        "This command changes the authentication password required to connect to this managed node."
        "The default value is 'youshallnotpass'."
    ),
    "command_llsetup_config_server_port": _(
        "This command changes the connection port used to connect to this managed node, "
        "only change this if the default port '2333' is causing conflicts with existing applications."
    ),
    "command_llsetup_config_source_http": _(
        "This command toggles the support of direct url streams like Icecast or Shoutcast streams. "
        "An example is <http://ice6.somafm.com/gsclassic-128-mp3>; "
        "Disabling this will make the bot unable to play any direct url steam content."
    ),
    "command_llsetup_config_source_bandcamp": _(
        "This command toggles the support of Bandcamp audio playback. "
        "An example is <http://deaddiskdrive.bandcamp.com/track/crystal-glass>; "
        "Disabling this will make the bot unable to play any Bandcamp content",
    ),
    "command_llsetup_config_source_local": _(
        "This command toggles the support of local track audio playback. "
        "for example `/mnt/data/my_super_funky_track.mp3`; "
        "Disabling this will make the bot unable to play any local track content."
    ),
    "command_llsetup_config_source_soundcloud": _(
        "This command toggles the support of Soundcloud playback. "
        "An example is <https://soundcloud.com/user-103858850/tilla>; "
        "Disabling this will make the bot unable to play any Soundcloud content."
    ),
    "command_llsetup_config_source_youtube": _(
        "This command toggles the support of YouTube playback (Spotify depends on YouTube). "
        "Disabling this will make the bot unable to play any YouTube content, "
        "this includes Spotify."
    ),
    "command_llsetup_config_source_twitch": _(
        "This command toggles the support of Twitch playback. "
        "An example of this is <https://twitch.tv/monstercat>; "
        "Disabling this will make the bot unable to play any Twitch content."
    ),
    "command_llsetup_config_source_vimeo": _(
        "This command toggles the support of Vimeo playback. "
        "An example of this is <https://vimeo.com/157743578>; "
        "Disabling this will make the bot unable to play any Vimeo content."
    ),
    "command_llsetup_config_server_framebuffer": _(
        "This setting controls the managed nodes framebuffer, "
        "Do not change this unless instructed."
    ),
    "command_llsetup_config_server_buffer": _(
        "This setting controls the managed nodes NAS buffer, "
        "Do not change this unless instructed."
    ),
    "command_llsetup_reset": _("This command will reset every setting changed by `[p]llset`."),
}


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


# Both DataReader and DataWriter are taken from https://github.com/Devoxin/Lavalink.py/blob/master/lavalink/datarw.py
# These are licenced under MIT, Thanks Devoxin for putting these together!
# The license can be found in https://github.com/Devoxin/Lavalink.py/blob/master/LICENSE


class DataReader:
    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, n):
        return self._buf.read(n)

    def read_byte(self):
        return self._read(1)

    def read_boolean(self):
        (result,) = struct.unpack("B", self.read_byte())
        return result != 0

    def read_unsigned_short(self):
        (result,) = struct.unpack(">H", self._read(2))
        return result

    def read_int(self):
        (result,) = struct.unpack(">i", self._read(4))
        return result

    def read_long(self):
        (result,) = struct.unpack(">Q", self._read(8))
        return result

    def read_utf(self):
        text_length = self.read_unsigned_short()
        return self._read(text_length)


class DataWriter:
    def __init__(self):
        self._buf = BytesIO()

    def _write(self, data):
        self._buf.write(data)

    def write_byte(self, byte):
        self._buf.write(byte)

    def write_boolean(self, b):
        enc = struct.pack("B", 1 if b else 0)
        self.write_byte(enc)

    def write_unsigned_short(self, s):
        enc = struct.pack(">H", s)
        self._write(enc)

    def write_int(self, i):
        enc = struct.pack(">i", i)
        self._write(enc)

    def write_long(self, l):
        enc = struct.pack(">Q", l)
        self._write(enc)

    def write_utf(self, s):
        utf = s.encode("utf8")
        byte_len = len(utf)

        if byte_len > 65535:
            raise OverflowError("UTF string may not exceed 65535 bytes!")

        self.write_unsigned_short(byte_len)
        self._write(utf)

    def finish(self):
        with BytesIO() as track_buf:
            byte_len = self._buf.getbuffer().nbytes
            flags = byte_len | (1 << 30)
            enc_flags = struct.pack(">i", flags)
            track_buf.write(enc_flags)

            self._buf.seek(0)
            track_buf.write(self._buf.read())
            self._buf.close()

            track_buf.seek(0)
            return track_buf.read()
