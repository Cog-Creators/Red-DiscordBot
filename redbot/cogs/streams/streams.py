import contextlib
import logging

import discord
from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import pagify
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from .streamtypes import (
    Stream,
    TwitchStream,
    HitboxStream,
    MixerStream,
    PicartoStream,
    YoutubeStream,
    Game,
    TwitchGame,
    TWITCH_GAMES_ENDPOINT,
)
from .errors import (
    OfflineStream,
    StreamNotFound,
    APIError,
    InvalidYoutubeCredentials,
    StreamsError,
    InvalidTwitchCredentials,
    GameNotInStreamTargetGameList,
    OfflineGame,
)
from . import streamtypes as _streamtypes
from collections import defaultdict
import asyncio
import re
from typing import Optional, List, Tuple
import aiohttp

CHECK_DELAY = 60

log = logging.getLogger("red.streams")

_ = Translator("Streams", __file__)


@cog_i18n(_)
class Streams(commands.Cog):

    global_defaults = {"tokens": {}, "streams": [], "games": [], "known_games": {}}

    guild_defaults = {
        "autodelete": False,
        "mention_everyone": False,
        "mention_here": False,
        "live_message_mention": False,
        "live_message_nomention": False,
        "game_live_message_mention": False,
        "game_live_message_nomention": False,
    }

    role_defaults = {"mention": False}

    def __init__(self, bot: Red):
        super().__init__()
        self.db = Config.get_conf(self, 26262626)

        self.db.register_global(**self.global_defaults)

        self.db.register_guild(**self.guild_defaults)

        self.db.register_role(**self.role_defaults)

        self.bot: Red = bot

        self.streams: List[Stream] = []
        self.streams_task: Optional[asyncio.Task] = None
        self.games_task: Optional[asyncio.Task] = None
        self.twitch_access_token = None

        self.yt_cid_pattern = re.compile("^UC[-_A-Za-z0-9]{21}[AQgw]$")

    def check_name_or_id(self, data: str):
        matched = self.yt_cid_pattern.fullmatch(data)
        if matched is None:
            return True
        return False

    async def initialize(self) -> None:
        """Should be called straight after cog instantiation."""
        await self.move_api_keys()
        await self.get_twitch_access_token()
        self.streams = await self.load_streams()
        self.games = await self.load_games()

        self.streams_task = self.bot.loop.create_task(self._stream_alerts())
        self.games_task = self.bot.loop.create_task(self._game_alerts())

    async def move_api_keys(self):
        """Move the API keys from cog stored config to core bot config if they exist."""
        tokens = await self.db.tokens()
        youtube = await self.bot.db.api_tokens.get_raw("youtube", default={})
        twitch = await self.bot.db.api_tokens.get_raw("twitch", default={})
        for token_type, token in tokens.items():
            if token_type == "YoutubeStream" and "api_key" not in youtube:
                await self.bot.db.api_tokens.set_raw("youtube", value={"api_key": token})
            if token_type == "TwitchStream" and "client_id" not in twitch:
                # Don't need to check Community since they're set the same
                await self.bot.db.api_tokens.set_raw("twitch", value={"client_id": token})
        await self.db.tokens.clear()

    @commands.command()
    async def twitchstream(self, ctx: commands.Context, channel_name: str):
        """Check if a Twitch channel is live."""
        token = await self.bot.db.api_tokens.get_raw("twitch", default=None)
        if not token:
            await ctx.send(
                _(
                    "No credentials have been configured. "
                    "See `{0.prefix}streamset twitchtoken` for more info"
                ).format(ctx)
            )
            return
        stream = TwitchStream(name=channel_name, token=token, bot=self.bot)
        await self.check_online(ctx, stream)

    @commands.command()
    async def youtubestream(self, ctx: commands.Context, channel_id_or_name: str):
        """Check if a YouTube channel is live."""
        apikey = await self.bot.db.api_tokens.get_raw("youtube", default={"api_key": None})
        is_name = self.check_name_or_id(channel_id_or_name)
        if is_name:
            stream = YoutubeStream(name=channel_id_or_name, token=apikey, bot=self.bot)
        else:
            stream = YoutubeStream(id=channel_id_or_name, token=apikey, bot=self.bot)
        await self.check_online(ctx, stream)

    @commands.command()
    async def hitbox(self, ctx: commands.Context, channel_name: str):
        """Check if a Hitbox channel is live."""
        stream = HitboxStream(name=channel_name, bot=self.bot)
        await self.check_online(ctx, stream)

    @commands.command()
    async def mixer(self, ctx: commands.Context, channel_name: str):
        """Check if a Mixer channel is live."""
        stream = MixerStream(name=channel_name, bot=self.bot)
        await self.check_online(ctx, stream)

    @commands.command()
    async def picarto(self, ctx: commands.Context, channel_name: str):
        """Check if a Picarto channel is live."""
        stream = PicartoStream(name=channel_name, bot=self.bot)
        await self.check_online(ctx, stream)

    async def check_online(self, ctx: commands.Context, stream):
        try:
            embed = await stream.is_online()
        except OfflineStream:
            await ctx.send(_("That user is offline."))
        except StreamNotFound:
            await ctx.send(_("That channel doesn't seem to exist."))
        except InvalidTwitchCredentials:
            await ctx.send(
                _(
                    "The Twitch token is either invalid or has not been set. See "
                    "`{prefix}streamset twitchtoken`."
                ).format(prefix=ctx.prefix)
            )
        except InvalidYoutubeCredentials:
            await ctx.send(
                _(
                    "The YouTube API key is either invalid or has not been set. See "
                    "`{prefix}streamset youtubekey`."
                ).format(prefix=ctx.prefix)
            )
        except GameNotInStreamTargetGameList:
            pass
        except APIError:
            await ctx.send(
                _("Something went wrong whilst trying to contact the stream service's API.")
            )
        else:
            await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @checks.mod()
    async def streamalert(self, ctx: commands.Context):
        """Manage automated stream alerts."""
        pass

    @streamalert.group(name="twitch", invoke_without_command=True)
    async def _twitch(self, ctx: commands.Context, channel_name: str = None):
        """Manage Twitch stream notifications."""
        if channel_name is not None:
            await ctx.invoke(self.twitch_alert_channel, channel_name)
        else:
            await ctx.send_help()

    @_twitch.command(name="channel")
    async def twitch_alert_channel(
        self, ctx: commands.Context, channel_name: str, games: Optional[str] = None
    ):
        """Toggle alerts in this channel for a Twitch stream.
        
        Optionally, games may be specified via a pipe-separated list (|), in which case alerts 
        will only be triggered for the channel if their game is set to one of those games.
        These names should be exactly how they appear on the game's page on Twitch."""
        if games:
            games = games.split("|")
        if re.fullmatch(r"<#\d+>", channel_name):
            await ctx.send("Please supply the name of a *Twitch* channel, not a Discord channel.")
            return
        await self.stream_alert(ctx, TwitchStream, channel_name.lower(), games=games)

    @_twitch.command(name="game")
    async def twitch_alert_game(self, ctx: commands.Context, sort: str, count: int, *, game: str):
        """Toggle alerts in this channel for a Twitch game.
        
        `sort` must be one of: 'random', 'top'
        `count` should be a number between 1 and 25
        `game` must be an exact match to the game name on its Twitch page"""
        game_data = {}
        if count < 1 or count > 25:
            await ctx.send(_("Count must be between 1 and 25!"))
            return
        try:
            game_list = await self.db.known_games.get_raw("twitch")
        except KeyError:
            game_list = []
        for g in game_list:
            if g["name"].lower() == game.lower():
                game_data = g
                break
        else:
            token = await self.bot.db.api_tokens.get_raw("twitch", default=None)
            if token:
                if token["access_token"]:
                    header = {"Authorization": "Bearer " + token["access_token"]}
                else:
                    header = {"Client-ID": str(token["client_id"])}
            else:
                await ctx.send(
                    _("No credentials available! Please see `[p]streamset twitchtoken` for help.")
                )
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TWITCH_GAMES_ENDPOINT, headers=header, params={"name": game}
                ) as game_data:
                    gd = await game_data.json(encoding="utf-8")
            if game_data.status == 200:
                if "data" in gd and gd["data"]:
                    game = gd["data"][0]
                    game_data = game
                    game_list.append(game)
                    await self.db.known_games.set_raw("twitch", value=game_list)
                else:
                    await ctx.send(
                        _(
                            "I was unable to find a game by that name! "
                            "Please confirm you have entered the name correctly."
                        )
                    )
                    return

        await self.game_alert(ctx, TwitchGame, sort, count, game_data)

    @streamalert.command(name="youtube")
    async def youtube_alert(self, ctx: commands.Context, channel_name_or_id: str):
        """Toggle alerts in this channel for a YouTube stream."""
        await self.stream_alert(ctx, YoutubeStream, channel_name_or_id)

    @streamalert.command(name="hitbox")
    async def hitbox_alert(self, ctx: commands.Context, channel_name: str):
        """Toggle alerts in this channel for a Hitbox stream."""
        await self.stream_alert(ctx, HitboxStream, channel_name)

    @streamalert.command(name="mixer")
    async def mixer_alert(self, ctx: commands.Context, channel_name: str):
        """Toggle alerts in this channel for a Mixer stream."""
        await self.stream_alert(ctx, MixerStream, channel_name)

    @streamalert.command(name="picarto")
    async def picarto_alert(self, ctx: commands.Context, channel_name: str):
        """Toggle alerts in this channel for a Picarto stream."""
        await self.stream_alert(ctx, PicartoStream, channel_name)

    @streamalert.command(name="stop", usage="[disable_all=No]")
    async def streamalert_stop(self, ctx: commands.Context, _all: bool = False):
        """Disable all stream alerts in this channel or server.

        `[p]streamalert stop` will disable this channel's stream
        alerts.

        Do `[p]streamalert stop yes` to disable all stream alerts in
        this server.
        """
        streams = self.streams.copy()
        games = self.games.copy()

        local_channel_ids = [c.id for c in ctx.guild.channels]
        to_remove = []

        for stream in streams:
            for channel_id in stream.channels:
                if channel_id == ctx.channel.id:
                    stream.channels.remove(channel_id)
                elif _all and ctx.channel.id in local_channel_ids:
                    if channel_id in stream.channels:
                        stream.channels.remove(channel_id)

            if not stream.channels:
                to_remove.append(stream)

        for stream in to_remove:
            streams.remove(stream)

        to_remove = []
        for game in games:
            for channel_id in game.channels:
                if channel_id == ctx.channel.id:
                    game.channels.remove(channel_id)
                elif _all and ctx.channel.id in local_channel_ids:
                    if channel_id in game.channels:
                        gamestream.channels.remove(channel_id)
            if not game.channels:
                to_remove.append(game)

        for game in to_remove:
            games.remove(game)

        self.streams = streams
        self.games = games
        await self.save_streams()
        await self.save_games()

        if _all:
            msg = _("All the stream alerts in this server have been disabled.")
        else:
            msg = _("All the stream alerts in this channel have been disabled.")

        await ctx.send(msg)

    @streamalert.command(name="list")
    async def streamalert_list(self, ctx: commands.Context):
        """List all active stream alerts in this server."""
        streams_list = defaultdict(list)
        guild_channels_ids = [c.id for c in ctx.guild.channels]
        msg = _("Active alerts:\n\n")

        for stream in self.streams:
            for channel_id in stream.channels:
                if channel_id in guild_channels_ids:
                    streams_list[channel_id].append(stream.name.lower())

        if not streams_list:
            await ctx.send(_("There are no active alerts in this server."))
            return

        for channel_id, streams in streams_list.items():
            channel = ctx.guild.get_channel(channel_id)
            msg += "** - #{}**\n{}\n".format(channel, ", ".join(streams))

        for page in pagify(msg):
            await ctx.send(page)

    async def game_alert(
        self, ctx: commands.Context, _class, sort: str, count: int, game_data: dict
    ):
        game = self.get_game(_class, game_data)
        if not game:
            token = await self.bot.db.api_tokens.get_raw(_class.token_name, default=None)
            is_twitch = _class.__name__ == "TwitchGame"
            if is_twitch:
                game = _class(
                    name=game_data["name"],
                    id=game_data["id"],
                    box_art_url=game_data["box_art_url"],
                    token=token,
                    bot=self.bot,
                    sort=sort,
                    count=count,
                )
            else:
                game = _class(
                    name=game_data["name"],
                    id=game_data["id"],
                    bot=self.bot,
                    sort=sort,
                    count=count,
                )
        await self.add_or_remove_game(ctx, game)

    async def stream_alert(self, ctx: commands.Context, _class, channel_name, games: list = None):
        stream = self.get_stream(_class, channel_name)
        if not stream:
            token = await self.bot.db.api_tokens.get_raw(_class.token_name, default=None)
            is_yt = _class.__name__ == "YoutubeStream"
            is_twitch = _class.__name__ == "TwitchStream"
            if is_yt and not self.check_name_or_id(channel_name):
                stream = _class(id=channel_name, token=token, bot=self.bot)
            elif is_twitch and games is not None:
                game_id_list = []
                if token["access_token"]:
                    header = {"Authorization": "Bearer " + token["access_token"]}
                else:
                    header = {"Client-ID": str(token["client_id"])}
                for game in games:
                    async with aiohttp.ClientSession as session:
                        async with session.get(
                            "https://api.twitch.tv/helix/games",
                            headers=header,
                            params={"name": game},
                        ) as r:
                            data = await r.json()
                    if r.status == 200:
                        if "data" in data and data["data"]:
                            game_id_list.append(data["data"][0]["id"])
                stream = _class(name=channel_name, token=token, bot=self.bot, games=game_id_list)
            else:
                stream = _class(name=channel_name, token=token, bot=self.bot)
            try:
                exists = await self.check_exists(stream)
            except InvalidTwitchCredentials:
                await ctx.send(
                    _(
                        "The Twitch token is either invalid or has not been set. See "
                        "`{prefix}streamset twitchtoken`."
                    ).format(prefix=ctx.prefix)
                )
                return
            except InvalidYoutubeCredentials:
                await ctx.send(
                    _(
                        "The YouTube API key is either invalid or has not been set. See "
                        "`{prefix}streamset youtubekey`."
                    ).format(prefix=ctx.prefix)
                )
                return
            except APIError:
                await ctx.send(
                    _("Something went wrong whilst trying to contact the stream service's API.")
                )
                return
            else:
                if not exists:
                    await ctx.send(_("That channel doesn't seem to exist."))
                    return

        await self.add_or_remove(ctx, stream)

    @commands.group()
    @checks.mod()
    async def streamset(self, ctx: commands.Context):
        """Set tokens for accessing streams."""
        pass

    @streamset.command()
    @checks.is_owner()
    async def twitchtoken(self, ctx: commands.Context):
        """Explain how to set the twitch token."""

        message = _(
            "To set the twitch API tokens, follow these steps:\n"
            "1. Go to this page: https://dev.twitch.tv/dashboard/apps.\n"
<<<<<<< HEAD
            "2. Click *Register Your Application*\n"
            "3. Enter a name, set the OAuth Redirect URI to `http://localhost`, and \n"
            "select an Application Category of your choosing."
            "4. Click *Register*, and on the following page, click *New Secret* under Client Secret.\n"
            "5. do `{prefix}set api twitch client_id,your_client_id client_secret,your_client_secret`\n\n"
=======
            "2. Click *Register Your Application*.\n"
            "3. Enter a name, set the OAuth Redirect URI to `http://localhost`, and "
            "select an Application Category of your choosing.\n"
            "4. Click *Register*.\n"
            "5. On the following page, copy the Client ID.\n"
            "6. Run the command `{prefix}set api twitch client_id,<your_client_id_here>`\n\n"
>>>>>>> release/V3/develop
            "Note: These tokens are sensitive and should only be used in a private channel\n"
            "or in DM with the bot.\n"
        ).format(prefix=ctx.prefix)

        await ctx.maybe_send_embed(message)

    @streamset.command()
    @checks.is_owner()
    async def youtubekey(self, ctx: commands.Context):
        """Explain how to set the YouTube token."""

        message = _(
            "To get one, do the following:\n"
            "1. Create a project\n"
            "(see https://support.google.com/googleapi/answer/6251787 for details)\n"
            "2. Enable the YouTube Data API v3 \n"
            "(see https://support.google.com/googleapi/answer/6158841 for instructions)\n"
            "3. Set up your API key \n"
            "(see https://support.google.com/googleapi/answer/6158862 for instructions)\n"
            "4. Copy your API key and run the command "
            "`{prefix}set api youtube api_key,<your_api_key_here>`\n\n"
            "Note: These tokens are sensitive and should only be used in a private channel\n"
            "or in DM with the bot.\n"
        ).format(prefix=ctx.prefix)

        await ctx.maybe_send_embed(message)

    @streamset.group()
    @commands.guild_only()
    async def message(self, ctx: commands.Context):
        """Manage custom message for stream alerts."""
        pass

    @message.group(name="game")
    @commands.guild_only()
    async def msg_game(self, ctx: commands.Context):
        """Manage custom message for game alerts."""
        pass

    @msg_game.command(name="mention")
    @commands.guild_only()
    async def game_with_mention(self, ctx: commands.Context, message: str = None):
        """Set game alert message when mentions are enabled.

        Use `{mention}` in the message to insert the selected mentions.

        Use `{game.name}` in the message to insert the game name.

        For example: `[p]streamset message game mention "{mention}, there are channels currently playing {game.name}!"`
        """
        if message is not None:
            guild = ctx.guild
            await self.db.guild(guild).game_live_message_mention.set(message)
            await ctx.send(_("game alert message set!"))
        else:
            await ctx.send_help()

    @msg_game.command(name="nomention")
    @commands.guild_only()
    async def game_no_mention(self, ctx: commands.Context, message: str = None):
        """Set game alert message when mentions are disabled.

        Use `{game.name}` in the message to insert the game name.

        For example: `[p]streamset message game nomention "There are channels currently playing {game.name}!"`
        """
        if message is not None:
            guild = ctx.guild
            await self.db.guild(guild).game_live_message_nomention.set(message)
            await ctx.send(_("game alert message set!"))
        else:
            await ctx.send_help()

    @msg_game.command(name="clear")
    @commands.guild_only()
    async def game_clear_message(self, ctx: commands.Context):
        """Reset the game alert messages in this server."""
        guild = ctx.guild
        await self.db.guild(guild).game_live_message_mention.set(False)
        await self.db.guild(guild).game_live_message_nomention.set(False)
        await ctx.send(_("Game alerts in this server will now use the default alert message."))

    @message.command(name="mention")
    @commands.guild_only()
    async def with_mention(self, ctx: commands.Context, message: str = None):
        """Set stream alert message when mentions are enabled.

        Use `{mention}` in the message to insert the selected mentions.

        Use `{stream.name}` in the message to insert the channel or user name.

        For example: `[p]streamset message mention "{mention}, {stream.name} is live!"`
        """
        if message is not None:
            guild = ctx.guild
            await self.db.guild(guild).live_message_mention.set(message)
            await ctx.send(_("stream alert message set!"))
        else:
            await ctx.send_help()

    @message.command(name="nomention")
    @commands.guild_only()
    async def without_mention(self, ctx: commands.Context, message: str = None):
        """Set stream alert message when mentions are disabled.

        Use `{stream.name}` in the message to insert the channel or user name.

        For example: `[p]streamset message nomention "{stream.name} is live!"`
        """
        if message is not None:
            guild = ctx.guild
            await self.db.guild(guild).live_message_nomention.set(message)
            await ctx.send(_("stream alert message set!"))
        else:
            await ctx.send_help()

    @message.command(name="clear")
    @commands.guild_only()
    async def clear_message(self, ctx: commands.Context):
        """Reset the stream alert messages in this server."""
        guild = ctx.guild
        await self.db.guild(guild).live_message_mention.set(False)
        await self.db.guild(guild).live_message_nomention.set(False)
        await ctx.send(_("Stream alerts in this server will now use the default alert message."))

    @streamset.group()
    @commands.guild_only()
    async def mention(self, ctx: commands.Context):
        """Manage mention settings for stream alerts."""
        pass

    @mention.command(aliases=["everyone"])
    @commands.guild_only()
    async def all(self, ctx: commands.Context):
        """Toggle the `@\u200beveryone` mention."""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).mention_everyone()
        if current_setting:
            await self.db.guild(guild).mention_everyone.set(False)
            await ctx.send(_("`@\u200beveryone` will no longer be mentioned for stream alerts."))
        else:
            await self.db.guild(guild).mention_everyone.set(True)
            await ctx.send(_("When a stream is live, `@\u200beveryone` will be mentioned."))

    @mention.command(aliases=["here"])
    @commands.guild_only()
    async def online(self, ctx: commands.Context):
        """Toggle the `@\u200bhere` mention."""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).mention_here()
        if current_setting:
            await self.db.guild(guild).mention_here.set(False)
            await ctx.send(_("`@\u200bhere` will no longer be mentioned for stream alerts."))
        else:
            await self.db.guild(guild).mention_here.set(True)
            await ctx.send(_("When a stream is live, `@\u200bhere` will be mentioned."))

    @mention.command()
    @commands.guild_only()
    async def role(self, ctx: commands.Context, *, role: discord.Role):
        """Toggle a role mention."""
        current_setting = await self.db.role(role).mention()
        if current_setting:
            await self.db.role(role).mention.set(False)
            await ctx.send(
                _("`@\u200b{role.name}` will no longer be mentioned for stream alerts.").format(
                    role=role
                )
            )
        else:
            await self.db.role(role).mention.set(True)
            msg = _(
                "When a stream or community is live, `@\u200b{role.name}` will be mentioned."
            ).format(role=role)
            if not role.mentionable:
                msg += " " + _(
                    "Since the role is not mentionable, it will be momentarily made mentionable "
                    "when announcing a streamalert. Please make sure I have the correct "
                    "permissions to manage this role, or else members of this role won't receive "
                    "a notification."
                )
            await ctx.send(msg)

    @streamset.command()
    @commands.guild_only()
    async def autodelete(self, ctx: commands.Context, on_off: bool):
        """Toggle alert deletion for when streams go offline."""
        await self.db.guild(ctx.guild).autodelete.set(on_off)
        if on_off:
            await ctx.send(_("The notifications will be deleted once streams go offline."))
        else:
            await ctx.send(_("Notifications will no longer be deleted."))

    async def add_or_remove(self, ctx: commands.Context, stream):
        if ctx.channel.id not in stream.channels:
            stream.channels.append(ctx.channel.id)
            if stream not in self.streams:
                self.streams.append(stream)
            await ctx.send(
                _(
                    "I'll now send a notification in this channel when {stream.name} is live."
                ).format(stream=stream)
            )
        else:
            stream.channels.remove(ctx.channel.id)
            if not stream.channels:
                self.streams.remove(stream)
            await ctx.send(
                _(
                    "I won't send notifications about {stream.name} in this channel anymore."
                ).format(stream=stream)
            )

        await self.save_streams()

    async def add_or_remove_game(self, ctx: commands.Context, game):
        if ctx.channel.id not in game.channels:
            game.channels.append(ctx.channel.id)
            if game not in self.games:
                self.games.append(game)
            await ctx.send(
                _(
                    "I'll now send a notification in this channel when {game.name} has live channels."
                ).format(game=game)
            )
        else:
            game.channels.remove(ctx.channel.id)
            if not game.channels:
                self.games.remove(game)
            await ctx.send(
                _("I won't send notifications about {game.name} in this channel anymore.").format(
                    game=game
                )
            )

        await self.save_games()

    def get_stream(self, _class, name):
        for stream in self.streams:
            # if isinstance(stream, _class) and stream.name == name:
            #    return stream
            # Reloading this cog causes an issue with this check ^
            # isinstance will always return False
            # As a workaround, we'll compare the class' name instead.
            # Good enough.
            if _class.__name__ == "YoutubeStream" and stream.type == _class.__name__:
                # Because name could be a username or a channel id
                if self.check_name_or_id(name) and stream.name.lower() == name.lower():
                    return stream
                elif not self.check_name_or_id(name) and stream.id == name:
                    return stream
            elif stream.type == _class.__name__ and stream.name.lower() == name.lower():
                return stream

    def get_game(self, _class, game_data):
        for game in self.games:
            if game.type == _class.__name__ and game.name.lower() == game_data["name"].lower():
                return game

    @staticmethod
    async def check_exists(stream):
        try:
            await stream.is_online()
        except OfflineStream:
            pass
        except StreamNotFound:
            return False
        except StreamsError:
            raise
        return True

    async def _stream_alerts(self):
        while True:
            try:
                await self.check_streams()
            except asyncio.CancelledError:
                pass
            await asyncio.sleep(CHECK_DELAY)

    async def _game_alerts(self):
        while True:
            try:
                await self.check_games()
            except asyncio.CancelledError:
                pass
            await asyncio.sleep(CHECK_DELAY)

    async def check_streams(self):
        for stream in self.streams:
            with contextlib.suppress(Exception):
                try:
<<<<<<< HEAD
                    embed = await stream.is_online()
                except (OfflineStream, GameNotInStreamTargetGameList):
=======
                    if stream.__class__.__name__ == "TwitchStream":
                        embed, is_rerun = await stream.is_online()
                    else:
                        embed = await stream.is_online()
                        is_rerun = False
                except OfflineStream:
>>>>>>> release/V3/develop
                    if not stream._messages_cache:
                        continue
                    for message in stream._messages_cache:
                        with contextlib.suppress(Exception):
                            autodelete = await self.db.guild(message.guild).autodelete()
                            if autodelete:
                                await message.delete()
                    stream._messages_cache.clear()
                    await self.save_streams()
                else:
                    for channel_id in stream.channels:
                        channel = self.bot.get_channel(channel_id)
                        mention_str, edited_roles = await self._get_mention_str(channel.guild)

                        if mention_str:
                            alert_msg = await self.db.guild(channel.guild).live_message_mention()
                            if alert_msg:
                                content = alert_msg.format(mention=mention_str, stream=stream)
                            else:
                                content = _("{mention}, {stream.name} is live!").format(
                                    mention=mention_str, stream=stream
                                )
                        else:
                            alert_msg = await self.db.guild(channel.guild).live_message_nomention()
                            if alert_msg:
                                content = alert_msg.format(stream=stream)
                            else:
                                content = _("{stream.name} is live!").format(stream=stream)
                        if stream._messages_cache:
                            for m in stream._messages_cache:
                                await m.edit(content, embed=embed)
                        else:
                            m = await channel.send(content, embed=embed)
                            stream._messages_cache.append(m)
                        if edited_roles:
                            for role in edited_roles:
                                await role.edit(mentionable=False)
                        await self.save_streams()

    async def check_games(self):
        for game in self.games:
            with contextlib.suppress(Exception):
                try:
                    embed = await game.has_online_channels()
                except OfflineGame:
                    if not game._messages_cache:
                        continue
                    for message in game._messages_cache:
                        with contextlib.suppress(Exception):
                            autodelete = await self.db.guild(message.guild).autodelete()
                            if autodelete:
                                await message.delete()
                    game._messages_cache.clear()
                    await self.save_games()
                else:
                    for channel_id in game.channels:
                        channel = self.bot.get_channel(channel_id)
                        mention_str, edited_roles = await self._get_mention_str(channel.guild)
                        if mention_str:
                            alert_msg = await self.db.guild(
                                channel.guild
                            ).game_live_message_mention()
                            if alert_msg:
                                content = alert_msg.format(mention=mention_str, game=game)
                            else:
                                content = _(
                                    "{mention}, there are channels currently playing {game.name}!"
                                ).format(mention=mention_str, game=game)
                        else:
                            alert_msg = await self.db.guild(
                                channel.guild
                            ).game_live_message_nomention()
                            if alert_msg:
                                content = alert_msg.format(stream=stream)
                            else:
                                content = _(
                                    "There are channels currently playing {game.name}!"
                                ).format(game=game)
                        if game._messages_cache:
                            for m in game._messages_cache:
                                await m.edit(content, embed=embed)
                        else:
                            m = await channel.send(content, embed=embed)
                            game._messages_cache.append(m)
                        if edited_roles:
                            for role in edited_roles:
                                await role.edit(mentionable=False)
                        await self.save_games()

    async def get_twitch_access_token(self):
        try:
            token = await self.bot.db.api_tokens.get_raw("twitch")
        except KeyError:
            log.warning(
                "No credentials found. Twitch features will not work without proper credentials"
            )
            return
        if "access_token" in token and token["access_token"]:
            self.twitch_access_token = token["access_token"]
        data = {
            "client_id": token["client_id"],
            "client_secret": token["client_secret"],
            "grant_type": "client_credentials",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post("https://id.twitch.tv/oauth2/token", json=data) as r:
                if r.status == 200:
                    resp = await r.json()
                    self.twitch_access_token = resp["access_token"]
                    await self.bot.db.api_tokens.set_raw(
                        "twitch", "access_token", value=resp["access_token"]
                    )
                elif r.status == 400:
                    resp = await r.json()
                    raise InvalidTwitchCredentials(resp["message"])

    async def validate_twitch_access_token(self):
        while not self.bot.is_closed():
            if self.twitch_access_token:
                headers = {"Authorization": f"OAuth {self.twitch_access_token}"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://id.twitch.tv/oauth2/validate", headers=headers
                    ) as r:
                        if r.status == 401:  # Invalid access token
                            await self.get_twitch_access_token()
                        else:
                            await asyncio.sleep(3600)

    async def _get_mention_str(self, guild: discord.Guild) -> Tuple[str, List[discord.Role]]:
        """Returns a 2-tuple with the string containing the mentions, and a list of
        all roles which need to have their `mentionable` property set back to False.
        """
        settings = self.db.guild(guild)
        mentions = []
        edited_roles = []
        if await settings.mention_everyone():
            mentions.append("@everyone")
        if await settings.mention_here():
            mentions.append("@here")
        can_manage_roles = guild.me.guild_permissions.manage_roles
        for role in guild.roles:
            if await self.db.role(role).mention():
                if can_manage_roles and not role.mentionable:
                    try:
                        await role.edit(mentionable=True)
                    except discord.Forbidden:
                        # Might still be unable to edit role based on hierarchy
                        pass
                    else:
                        edited_roles.append(role)
                mentions.append(role.mention)
        return " ".join(mentions), edited_roles

    async def load_streams(self):
        streams = []

        for raw_stream in await self.db.streams():
            _class = getattr(_streamtypes, raw_stream["type"], None)
            if not _class:
                continue
            raw_msg_cache = raw_stream["messages"]
            raw_stream["_messages_cache"] = []
            raw_stream["bot"] = self.bot
            for raw_msg in raw_msg_cache:
                chn = self.bot.get_channel(raw_msg["channel"])
                if chn is not None:
                    try:
                        msg = await chn.fetch_message(raw_msg["message"])
                    except discord.HTTPException:
                        pass
                    else:
                        raw_stream["_messages_cache"].append(msg)
            token = await self.bot.db.api_tokens.get_raw(_class.token_name, default=None)
            if token is not None:
                raw_stream["token"] = token
            streams.append(_class(**raw_stream))

        return streams

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.db.streams.set(raw_streams)

    async def load_games(self):
        games = []
        for raw_game in await self.db.games():
            _class = getattr(_streamtypes, raw_game["type"], None)
            if not _class:
                continue
            raw_msg_cache = raw_game["messages"]
            raw_game["_messages_cache"] = []
            for raw_msg in raw_msg_cache:
                chn = self.bot.get_channel(raw_msg["channel"])
                if chn is not None:
                    try:
                        msg = await chn.fetch_message(raw_msg["message"])
                    except discord.HTTPException:
                        pass
                    else:
                        raw_game["_messages_cache"].append(msg)
            token = await self.bot.db.api_tokens.get_raw(_class.token_name, default=None)
            if token is not None:
                raw_game["token"] = token
            games.append(_class(**raw_game))
        return games

    async def save_games(self):
        raw_games = []
        for game in self.games:
            raw_games.append(game.export())

        await self.db.games.set(raw_games)

    def cog_unload(self):
        if self.streams_task:
            self.streams_task.cancel()
        if self.games_task:
            self.games_task.cancel()

    __del__ = cog_unload
