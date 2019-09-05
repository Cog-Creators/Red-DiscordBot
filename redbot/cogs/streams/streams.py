# Standard Library
import asyncio
import contextlib
import re

from collections import defaultdict
from typing import List, Optional, Tuple

# Red Dependencies
import discord

# Red Imports
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify

# Red Relative Imports
from . import streamtypes as _streamtypes
from .errors import (
    APIError,
    InvalidTwitchCredentials,
    InvalidYoutubeCredentials,
    OfflineStream,
    StreamNotFound,
    StreamsError,
)
from .streamtypes import (
    HitboxStream,
    MixerStream,
    PicartoStream,
    Stream,
    TwitchStream,
    YoutubeStream,
)

CHECK_DELAY = 60


_ = Translator("Streams", __file__)


@cog_i18n(_)
class Streams(commands.Cog):

    global_defaults = {"tokens": {}, "streams": []}

    guild_defaults = {
        "autodelete": False,
        "mention_everyone": False,
        "mention_here": False,
        "live_message_mention": False,
        "live_message_nomention": False,
        "ignore_reruns": False,
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
        self.task: Optional[asyncio.Task] = None

        self.yt_cid_pattern = re.compile("^UC[-_A-Za-z0-9]{21}[AQgw]$")

    def check_name_or_id(self, data: str):
        matched = self.yt_cid_pattern.fullmatch(data)
        if matched is None:
            return True
        return False

    async def initialize(self) -> None:
        """Should be called straight after cog instantiation."""
        await self.move_api_keys()
        self.streams = await self.load_streams()

        self.task = self.bot.loop.create_task(self._stream_alerts())

    async def move_api_keys(self):
        """Move the API keys from cog stored config to core bot config if they exist."""
        tokens = await self.db.tokens()
        youtube = await self.bot.get_shared_api_tokens("youtube")
        twitch = await self.bot.get_shared_api_tokens("twitch")
        for token_type, token in tokens.items():
            if token_type == "YoutubeStream" and "api_key" not in youtube:
                await self.bot.set_shared_api_tokens("youtube", api_key=token)
            if token_type == "TwitchStream" and "client_id" not in twitch:
                # Don't need to check Community since they're set the same
                await self.bot.set_shared_api_tokens("twitch", client_id=token)
        await self.db.tokens.clear()

    @commands.command()
    async def twitchstream(self, ctx: commands.Context, channel_name: str):
        """Check if a Twitch channel is live."""
        token = (await self.bot.get_shared_api_tokens("twitch")).get("client_id")
        stream = TwitchStream(name=channel_name, token=token)
        await self.check_online(ctx, stream)

    @commands.command()
    async def youtubestream(self, ctx: commands.Context, channel_id_or_name: str):
        """Check if a YouTube channel is live."""
        apikey = await self.bot.get_shared_api_tokens("youtube")
        is_name = self.check_name_or_id(channel_id_or_name)
        if is_name:
            stream = YoutubeStream(name=channel_id_or_name, token=apikey)
        else:
            stream = YoutubeStream(id=channel_id_or_name, token=apikey)
        await self.check_online(ctx, stream)

    @commands.command()
    async def hitbox(self, ctx: commands.Context, channel_name: str):
        """Check if a Hitbox channel is live."""
        stream = HitboxStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def mixer(self, ctx: commands.Context, channel_name: str):
        """Check if a Mixer channel is live."""
        stream = MixerStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def picarto(self, ctx: commands.Context, channel_name: str):
        """Check if a Picarto channel is live."""
        stream = PicartoStream(name=channel_name)
        await self.check_online(ctx, stream)

    async def check_online(self, ctx: commands.Context, stream):
        try:
            info = await stream.is_online()
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
        except APIError:
            await ctx.send(
                _("Something went wrong whilst trying to contact the stream service's API.")
            )
        else:
            if isinstance(info, tuple):
                embed, is_rerun = info
                ignore_reruns = await self.db.guild(ctx.channel.guild).ignore_reruns()
                if ignore_reruns and is_rerun:
                    await ctx.send(_("That user is offline."))
                    return
            else:
                embed = info
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
    async def twitch_alert_channel(self, ctx: commands.Context, channel_name: str):
        """Toggle alerts in this channel for a Twitch stream."""
        if re.fullmatch(r"<#\d+>", channel_name):
            await ctx.send(
                _("Please supply the name of a *Twitch* channel, not a Discord channel.")
            )
            return
        await self.stream_alert(ctx, TwitchStream, channel_name.lower())

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

        self.streams = streams
        await self.save_streams()

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

    async def stream_alert(self, ctx: commands.Context, _class, channel_name):
        stream = self.get_stream(_class, channel_name)
        if not stream:
            token = await self.bot.get_shared_api_tokens(_class.token_name)
            is_yt = _class.__name__ == "YoutubeStream"
            if is_yt and not self.check_name_or_id(channel_name):
                stream = _class(id=channel_name, token=token)
            else:
                stream = _class(name=channel_name, token=token)
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
            "2. Click *Register Your Application*.\n"
            "3. Enter a name, set the OAuth Redirect URI to `http://localhost`, and "
            "select an Application Category of your choosing.\n"
            "4. Click *Register*.\n"
            "5. On the following page, copy the Client ID.\n"
            "6. Run the command `{prefix}set api twitch client_id <your_client_id_here>`\n\n"
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
            "`{prefix}set api youtube api_key <your_api_key_here>`\n\n"
            "Note: These tokens are sensitive and should only be used in a private channel\n"
            "or in DM with the bot.\n"
        ).format(prefix=ctx.prefix)

        await ctx.maybe_send_embed(message)

    @streamset.group()
    @commands.guild_only()
    async def message(self, ctx: commands.Context):
        """Manage custom message for stream alerts."""
        pass

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
            await ctx.send(_("Stream alert message set!"))
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
            await ctx.send(_("Stream alert message set!"))
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

    @streamset.command(name="ignorereruns")
    @commands.guild_only()
    async def ignore_reruns(self, ctx: commands.Context):
        """Toggle excluding rerun streams from alerts."""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).ignore_reruns()
        if current_setting:
            await self.db.guild(guild).ignore_reruns.set(False)
            await ctx.send(_("Streams of type 'rerun' will be included in alerts."))
        else:
            await self.db.guild(guild).ignore_reruns.set(True)
            await ctx.send(_("Streams of type 'rerun' will no longer send an alert."))

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

    async def check_streams(self):
        for stream in self.streams:
            with contextlib.suppress(Exception):
                try:
                    if stream.__class__.__name__ == "TwitchStream":
                        embed, is_rerun = await stream.is_online()
                    else:
                        embed = await stream.is_online()
                        is_rerun = False
                except OfflineStream:
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
                    if stream._messages_cache:
                        continue
                    for channel_id in stream.channels:
                        channel = self.bot.get_channel(channel_id)
                        ignore_reruns = await self.db.guild(channel.guild).ignore_reruns()
                        if ignore_reruns and is_rerun:
                            continue
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

                        m = await channel.send(content, embed=embed)
                        stream._messages_cache.append(m)
                        if edited_roles:
                            for role in edited_roles:
                                await role.edit(mentionable=False)
                        await self.save_streams()

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

    async def filter_streams(self, streams: list, channel: discord.TextChannel) -> list:
        filtered = []
        for stream in streams:
            tw_id = str(stream["channel"]["_id"])
            for alert in self.streams:
                if isinstance(alert, TwitchStream) and alert.id == tw_id:
                    if channel.id in alert.channels:
                        break
            else:
                filtered.append(stream)
        return filtered

    async def load_streams(self):
        streams = []

        for raw_stream in await self.db.streams():
            _class = getattr(_streamtypes, raw_stream["type"], None)
            if not _class:
                continue
            raw_msg_cache = raw_stream["messages"]
            raw_stream["_messages_cache"] = []
            for raw_msg in raw_msg_cache:
                chn = self.bot.get_channel(raw_msg["channel"])
                if chn is not None:
                    try:
                        msg = await chn.fetch_message(raw_msg["message"])
                    except discord.HTTPException:
                        pass
                    else:
                        raw_stream["_messages_cache"].append(msg)
            token = await self.bot.get_shared_api_tokens(_class.token_name)
            if token:
                raw_stream["token"] = token
            streams.append(_class(**raw_stream))

        return streams

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.db.streams.set(raw_streams)

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    __del__ = cog_unload
