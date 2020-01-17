import asyncio
import contextlib
import functools
import logging
import re
from typing import MutableMapping, Optional
from urllib.parse import urlparse

import discord
import lavalink
import math
from fuzzywuzzy import process

from redbot.cogs.audio.audio_dataclasses import Query, LocalPath
from redbot.cogs.audio.cog import MixinMeta
from redbot.core import commands
from redbot.core.utils.chat_formatting import escape
from ..utils import _
from ...utils import PlaylistScope

log = logging.getLogger("red.cogs.Audio.cog.commands.utilities.StaticMethod")

_RE_TIME_CONVERTER = re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])")
_RE_YT_LIST_PLAYLIST = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.?be)(/playlist\?).*(list=)(.*)(&|$)"
)


class StaticMethodUtilities(MixinMeta):
    """
    All Static method utilities.
    """

    @staticmethod
    async def _build_search_page(ctx: commands.Context, tracks, page_num):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        command = ctx.invoked_with
        folder = False
        for i, track in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            try:
                query = Query.process_input(track.uri)
                if query.is_local:
                    search_list += "`{0}.` **{1}**\n[{2}]\n".format(
                        search_track_num, track.title, LocalPath(track.uri).to_string_user(),
                    )
                else:
                    search_list += "`{0}.` **[{1}]({2})**\n".format(
                        search_track_num, track.title, track.uri
                    )
            except AttributeError:
                track = Query.process_input(track)
                if track.is_local and command != "search":
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
                    if track.is_album:
                        folder = True
                elif command == "search":
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
                else:
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
            await asyncio.sleep(0)
        if hasattr(tracks[0], "uri") and hasattr(tracks[0], "track_identifier"):
            title = _("Tracks Found:")
            footer = _("search results")
        elif folder:
            title = _("Folders Found:")
            footer = _("local folders")
        else:
            title = _("Files Found:")
            footer = _("local tracks")
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=(_("Page {page_num}/{total_pages}") + " | {num_results} {footer}").format(
                page_num=page_num,
                total_pages=search_num_pages,
                num_results=len(tracks),
                footer=footer,
            )
        )
        return embed

    @staticmethod
    def track_limit(track, maxlength) -> bool:
        try:
            length = round(track.length / 1000)
        except AttributeError:
            length = round(track / 1000)

        if maxlength < length <= 900000000000000:  # livestreams return 9223372036854775807ms
            return False
        return True

    async def is_allowed(self, guild: discord.Guild, query: str, query_obj: Query = None) -> bool:

        query = query.lower().strip()
        if query_obj is not None:
            query = query_obj.lavalink_query.replace("ytsearch:", "youtubesearch").replace(
                "scsearch:", "soundcloudsearch"
            )
        global_whitelist = set(await self.config.url_keyword_whitelist())
        global_whitelist = [i.lower() for i in global_whitelist]
        if global_whitelist:
            return any(i in query for i in global_whitelist)
        global_blacklist = set(await self.config.url_keyword_blacklist())
        global_blacklist = [i.lower() for i in global_blacklist]
        if any(i in query for i in global_blacklist):
            return False
        if guild is not None:
            whitelist = set(await self.config.guild(guild).url_keyword_whitelist())
            whitelist = [i.lower() for i in whitelist]
            if whitelist:
                return any(i in query for i in whitelist)
            blacklist = set(await self.config.guild(guild).url_keyword_blacklist())
            blacklist = [i.lower() for i in blacklist]
            return not any(i in query for i in blacklist)
        return True

    @staticmethod
    async def queue_duration(ctx) -> int:
        player = lavalink.get_player(ctx.guild.id)
        duration = []
        for i in range(len(player.queue)):
            if not player.queue[i].is_stream:
                duration.append(player.queue[i].length)
        queue_dur = sum(duration)
        if not player.queue:
            queue_dur = 0
        try:
            if not player.current.is_stream:
                remain = player.current.length - player.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        queue_total_duration = remain + queue_dur
        return queue_total_duration

    @staticmethod
    async def draw_time(ctx) -> str:
        player = lavalink.get_player(ctx.guild.id)
        paused = player.paused
        pos = player.position
        dur = player.current.length
        sections = 12
        loc_time = round((pos / dur) * sections)
        bar = "\N{BOX DRAWINGS HEAVY HORIZONTAL}"
        seek = "\N{RADIO BUTTON}"
        if paused:
            msg = "\N{DOUBLE VERTICAL BAR}"
        else:
            msg = "\N{BLACK RIGHT-POINTING TRIANGLE}"
        for i in range(sections):
            if i == loc_time:
                msg += seek
            else:
                msg += bar
        return msg

    @staticmethod
    def dynamic_time(seconds) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d > 0:
            msg = "{0}d {1}h"
        elif d == 0 and h > 0:
            msg = "{1}h {2}m"
        elif d == 0 and h == 0 and m > 0:
            msg = "{2}m {3}s"
        elif d == 0 and h == 0 and m == 0 and s > 0:
            msg = "{3}s"
        else:
            msg = ""
        return msg.format(d, h, m, s)

    @staticmethod
    def match_url(url) -> bool:
        try:
            query_url = urlparse(url)
            return all([query_url.scheme, query_url.netloc, query_url.path])
        except Exception:
            return False

    @staticmethod
    def match_yt_playlist(url) -> bool:
        if _RE_YT_LIST_PLAYLIST.match(url):
            return True
        return False

    @staticmethod
    async def remove_react(message, react_emoji, react_user) -> None:
        with contextlib.suppress(discord.HTTPException):
            await message.remove_reaction(react_emoji, react_user)

    @staticmethod
    def get_track_description(track) -> Optional[str]:
        if track and getattr(track, "uri", None):
            query = Query.process_input(track.uri)
            if query.is_local or "localtracks/" in track.uri:
                if track.title != "Unknown title":
                    return f'**{escape(f"{track.author} - {track.title}")}**' + escape(
                        f"\n{query.to_string_user()} "
                    )
                else:
                    return escape(query.to_string_user())
            else:
                return f'**{escape(f"[{track.title}]({track.uri}) ")}**'
        elif hasattr(track, "to_string_user") and track.is_local:
            return escape(track.to_string_user() + " ")

    @staticmethod
    def get_track_description_unformatted(track) -> Optional[str]:
        if track and hasattr(track, "uri"):
            query = Query.process_input(track.uri)
            if query.is_local or "localtracks/" in track.uri:
                if track.title != "Unknown title":
                    return escape(f"{track.author} - {track.title}")
                else:
                    return escape(query.to_string_user())
            else:
                return escape(f"{track.title}")
        elif hasattr(track, "to_string_user") and track.is_local:
            return escape(track.to_string_user() + " ")

    @staticmethod
    def track_to_json(track: lavalink.Track) -> MutableMapping:
        track_keys = track._info.keys()
        track_values = track._info.values()
        track_id = track.track_identifier
        track_info = {}
        for k, v in zip(track_keys, track_values):
            track_info[k] = v
        keys = ["track", "info"]
        values = [track_id, track_info]
        track_obj = {}
        for key, value in zip(keys, values):
            track_obj[key] = value
        return track_obj

    @staticmethod
    def time_convert(length) -> int:
        match = _RE_TIME_CONVERTER.match(length)
        if match is not None:
            hr = int(match.group(1)) if match.group(1) else 0
            mn = int(match.group(2)) if match.group(2) else 0
            sec = int(match.group(3)) if match.group(3) else 0
            pos = sec + (mn * 60) + (hr * 3600)
            return pos
        else:
            try:
                return int(length)
            except ValueError:
                return 0

    @staticmethod
    def url_check(url) -> bool:
        valid_tld = [
            "youtube.com",
            "youtu.be",
            "soundcloud.com",
            "bandcamp.com",
            "vimeo.com",
            "beam.pro",
            "mixer.com",
            "twitch.tv",
            "spotify.com",
            "localtracks",
        ]
        query_url = urlparse(url)
        url_domain = ".".join(query_url.netloc.split(".")[-2:])
        if not query_url.netloc:
            url_domain = ".".join(query_url.path.split("/")[0].split(".")[-2:])
        return True if url_domain in valid_tld else False

    @staticmethod
    def userlimit(channel) -> bool:
        if channel.user_limit == 0 or channel.user_limit > len(channel.members) + 1:
            return False
        return True

    @staticmethod
    def rgetattr(obj, attr, *args):
        def _getattr(obj2, attr2):
            return getattr(obj2, attr2, *args)

        return functools.reduce(_getattr, [obj] + attr.split("."))

    @staticmethod
    def humanize_scope(scope, ctx=None, the=None):

        if scope == PlaylistScope.GLOBAL.value:
            return (_("the ") if the else "") + _("Global")
        elif scope == PlaylistScope.GUILD.value:
            return ctx.name if ctx else (_("the ") if the else "") + _("Server")
        elif scope == PlaylistScope.USER.value:
            return str(ctx) if ctx else (_("the ") if the else "") + _("User")

    @staticmethod
    async def is_requester(ctx: commands.Context, member: discord.Member):
        try:
            player = lavalink.get_player(ctx.guild.id)
            log.debug(f"Current requester is {player.current}")
            return player.current.requester.id == member.id
        except Exception as e:
            log.error(e)
        return False

    @staticmethod
    async def _apply_gain(guild_id: int, band, gain):
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": band, "gain": gain}],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    @staticmethod
    async def _apply_gains(guild_id: int, gains):
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": x, "gain": y} for x, y in enumerate(gains)],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    @staticmethod
    async def _eq_msg_clear(eq_message: discord.Message):
        if eq_message is not None:
            with contextlib.suppress(discord.HTTPException):
                await eq_message.delete()

    @staticmethod
    async def _genre_search_button_action(
        ctx: commands.Context, options, emoji, page, playlist=False
    ):
        try:
            if emoji == "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[0 + (page * 5)]
            elif emoji == "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[1 + (page * 5)]
            elif emoji == "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[2 + (page * 5)]
            elif emoji == "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[3 + (page * 5)]
            elif emoji == "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[4 + (page * 5)]
            else:
                search_choice = options[0 + (page * 5)]
        except IndexError:
            search_choice = options[-1]
        if not playlist:
            return list(search_choice.items())[0]
        else:
            return search_choice.get("uri")

    @staticmethod
    async def _build_genre_search_page(
        ctx: commands.Context, tracks, page_num, title, playlist=False
    ):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        for i, entry in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            if playlist:
                name = "**[{}]({})** - {}".format(
                    entry.get("name"),
                    entry.get("url"),
                    str(entry.get("tracks")) + " " + _("tracks"),
                )
            else:
                name = f"{list(entry.keys())[0]}"
            search_list += "`{}.` {}\n".format(search_track_num, name)
            await asyncio.sleep(0)

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages}").format(
                page_num=page_num, total_pages=search_num_pages
            )
        )
        return embed

    @staticmethod
    async def _build_playlist_list_page(ctx: commands.Context, page_num, abc_names, scope):
        plist_num_pages = math.ceil(len(abc_names) / 5)
        plist_idx_start = (page_num - 1) * 5
        plist_idx_end = plist_idx_start + 5
        plist = ""
        for i, playlist_info in enumerate(
            abc_names[plist_idx_start:plist_idx_end], start=plist_idx_start
        ):
            item_idx = i + 1
            plist += "`{}.` {}".format(item_idx, playlist_info)
            await asyncio.sleep(0)
        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Playlists for {scope}:").format(scope=scope),
            description=plist,
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num} playlists.").format(
                page_num=page_num, total_pages=plist_num_pages, num=len(abc_names)
            )
        )
        return embed

    @staticmethod
    async def _build_local_search_list(to_search, search_words):
        to_search_string = {i.track.name for i in to_search}
        search_results = process.extract(search_words, to_search_string, limit=50)
        search_list = []
        for track_match, percent_match in search_results:
            if percent_match > 60:
                search_list.extend(
                    [i.track.to_string_user() for i in to_search if i.track.name == track_match]
                )
            await asyncio.sleep(0)
        return search_list

    @staticmethod
    async def track_remaining_duration(ctx) -> int:
        player = lavalink.get_player(ctx.guild.id)
        if not player.current:
            return 0
        try:
            if not player.current.is_stream:
                remain = player.current.length - player.position
            else:
                remain = 0
        except AttributeError:
            remain = 0
        return remain
