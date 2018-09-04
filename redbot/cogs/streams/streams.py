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
    TwitchCommunity,
    YoutubeStream,
)
from .errors import (
    OfflineStream,
    StreamNotFound,
    APIError,
    InvalidYoutubeCredentials,
    CommunityNotFound,
    OfflineCommunity,
    StreamsError,
    InvalidTwitchCredentials,
)
from . import streamtypes as StreamClasses
from collections import defaultdict
import asyncio
import re
from typing import Optional, List

CHECK_DELAY = 60


_ = Translator("Streams", __file__)


@cog_i18n(_)
class Streams:

    global_defaults = {"tokens": {}, "streams": [], "communities": []}

    guild_defaults = {"autodelete": False, "mention_everyone": False, "mention_here": False}

    role_defaults = {"mention": False}

    def __init__(self, bot: Red):
        self.db = Config.get_conf(self, 26262626)

        self.db.register_global(**self.global_defaults)

        self.db.register_guild(**self.guild_defaults)

        self.db.register_role(**self.role_defaults)

        self.bot: Red = bot

        self.streams: List[Stream] = []
        self.communities: List[TwitchCommunity] = []
        self.task: Optional[asyncio.Task] = None

        self.yt_cid_pattern = re.compile("^UC[-_A-Za-z0-9]{21}[AQgw]$")

    def check_name_or_id(self, data: str):
        matched = self.yt_cid_pattern.fullmatch(data)
        if matched is None:
            return True
        return False

    async def initialize(self) -> None:
        """Should be called straight after cog instantiation."""
        self.streams = await self.load_streams()
        self.communities = await self.load_communities()

        self.task = self.bot.loop.create_task(self._stream_alerts())

    @commands.command()
    async def twitch(self, ctx: commands.Context, channel_name: str):
        """Checks if a Twitch channel is live"""
        token = await self.db.tokens.get_raw(TwitchStream.__name__, default=None)
        stream = TwitchStream(name=channel_name, token=token)
        await self.check_online(ctx, stream)

    @commands.command()
    async def youtube(self, ctx: commands.Context, channel_id_or_name: str):
        """Checks if a Youtube channel is live"""
        apikey = await self.db.tokens.get_raw(YoutubeStream.__name__, default=None)
        is_name = self.check_name_or_id(channel_id_or_name)
        if is_name:
            stream = YoutubeStream(name=channel_id_or_name, token=apikey)
        else:
            stream = YoutubeStream(id=channel_id_or_name, token=apikey)
        await self.check_online(ctx, stream)

    @commands.command()
    async def hitbox(self, ctx: commands.Context, channel_name: str):
        """Checks if a Hitbox channel is live"""
        stream = HitboxStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def mixer(self, ctx: commands.Context, channel_name: str):
        """Checks if a Mixer channel is live"""
        stream = MixerStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def picarto(self, ctx: commands.Context, channel_name: str):
        """Checks if a Picarto channel is live"""
        stream = PicartoStream(name=channel_name)
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
                _("The twitch token is either invalid or has not been set. See `{}`.").format(
                    "{}streamset twitchtoken".format(ctx.prefix)
                )
            )
        except InvalidYoutubeCredentials:
            await ctx.send(
                _("Your Youtube API key is either invalid or has not been set. See {}.").format(
                    "`{}streamset youtubekey`".format(ctx.prefix)
                )
            )
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
        pass

    @streamalert.group(name="twitch", autohelp=False)
    async def _twitch(self, ctx: commands.Context, channel_name: str = None):
        """Twitch stream alerts"""
        if channel_name is not None:
            await ctx.invoke(self.twitch_alert_channel, channel_name)
        else:
            await ctx.send_help()

    @_twitch.command(name="channel")
    async def twitch_alert_channel(self, ctx: commands.Context, channel_name: str):
        """Sets a Twitch alert notification in the channel"""
        if re.fullmatch(r"<#\d+>", channel_name):
            await ctx.send("Please supply the name of a *Twitch* channel, not a Discord channel.")
            return
        await self.stream_alert(ctx, TwitchStream, channel_name.lower())

    @_twitch.command(name="community")
    async def twitch_alert_community(self, ctx: commands.Context, community: str):
        """Sets an alert notification in the channel for the specified twitch community."""
        await self.community_alert(ctx, TwitchCommunity, community.lower())

    @streamalert.command(name="youtube")
    async def youtube_alert(self, ctx: commands.Context, channel_name_or_id: str):
        """Sets a Youtube alert notification in the channel"""
        await self.stream_alert(ctx, YoutubeStream, channel_name_or_id)

    @streamalert.command(name="hitbox")
    async def hitbox_alert(self, ctx: commands.Context, channel_name: str):
        """Sets a Hitbox alert notification in the channel"""
        await self.stream_alert(ctx, HitboxStream, channel_name)

    @streamalert.command(name="mixer")
    async def mixer_alert(self, ctx: commands.Context, channel_name: str):
        """Sets a Mixer alert notification in the channel"""
        await self.stream_alert(ctx, MixerStream, channel_name)

    @streamalert.command(name="picarto")
    async def picarto_alert(self, ctx: commands.Context, channel_name: str):
        """Sets a Picarto alert notification in the channel"""
        await self.stream_alert(ctx, PicartoStream, channel_name)

    @streamalert.command(name="stop")
    async def streamalert_stop(self, ctx: commands.Context, _all: bool = False):
        """Stops all stream notifications in the channel
        Adding 'yes' will disable all notifications in the server"""
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

        msg = _("All the alerts in the {} have been disabled.").format(
            "server" if _all else "channel"
        )

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
            token = await self.db.tokens.get_raw(_class.__name__, default=None)
            is_yt = _class.__name__ == "YoutubeStream"
            if is_yt and not self.check_name_or_id(channel_name):
                stream = _class(id=channel_name, token=token)
            else:
                stream = _class(name=channel_name, token=token)
            try:
                exists = await self.check_exists(stream)
            except InvalidTwitchCredentials:
                await ctx.send(
                    _("Your twitch token is either invalid or has not been set. See {}.").format(
                        "`{}streamset twitchtoken`".format(ctx.prefix)
                    )
                )
                return
            except InvalidYoutubeCredentials:
                await ctx.send(
                    _(
                        "Your Youtube API key is either invalid or has not been set. See {}."
                    ).format("`{}streamset youtubekey`".format(ctx.prefix))
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

    async def community_alert(self, ctx: commands.Context, _class, community_name):
        community = self.get_community(_class, community_name)
        if not community:
            token = await self.db.tokens.get_raw(_class.__name__, default=None)
            community = _class(name=community_name, token=token)
            try:
                await community.get_community_streams()
            except InvalidTwitchCredentials:
                await ctx.send(
                    _("The twitch token is either invalid or has not been set. See {}.").format(
                        "`{}streamset twitchtoken`".format(ctx.prefix)
                    )
                )
                return
            except CommunityNotFound:
                await ctx.send(_("That community doesn't seem to exist."))
                return
            except APIError:
                await ctx.send(
                    _("Something went wrong whilst trying to contact the stream service's API.")
                )
                return
            except OfflineCommunity:
                pass

        await self.add_or_remove_community(ctx, community)

    @commands.group()
    @checks.mod()
    async def streamset(self, ctx: commands.Context):
        pass

    @streamset.command()
    @checks.is_owner()
    async def twitchtoken(self, ctx: commands.Context, token: str):
        """Set the Client ID for twitch.
        To do this, follow these steps:
          1. Go to this page: https://dev.twitch.tv/dashboard/apps.
          2. Click *Register Your Application*
          3. Enter a name, set the OAuth Redirect URI to `http://localhost`, and
             select an Application Category of your choosing.
          4. Click *Register*, and on the following page, copy the Client ID.
          5. Paste the Client ID into this command. Done!
        """
        await self.db.tokens.set_raw("TwitchStream", value=token)
        await self.db.tokens.set_raw("TwitchCommunity", value=token)
        await ctx.send(_("Twitch token set."))

    @streamset.command()
    @checks.is_owner()
    async def youtubekey(self, ctx: commands.Context, key: str):
        """Sets the API key for Youtube.
        To get one, do the following:
        1. Create a project (see https://support.google.com/googleapi/answer/6251787 for details)
        2. Enable the Youtube Data API v3 (see https://support.google.com/googleapi/answer/6158841 for instructions)
        3. Set up your API key (see https://support.google.com/googleapi/answer/6158862 for instructions)
        4. Copy your API key and paste it into this command. Done!
        """
        await self.db.tokens.set_raw("YoutubeStream", value=key)
        await ctx.send(_("Youtube key set."))

    @streamset.group()
    @commands.guild_only()
    async def mention(self, ctx: commands.Context):
        """Sets mentions for alerts."""
        pass

    @mention.command(aliases=["everyone"])
    @commands.guild_only()
    async def all(self, ctx: commands.Context):
        """Toggles everyone mention"""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).mention_everyone()
        if current_setting:
            await self.db.guild(guild).mention_everyone.set(False)
            await ctx.send(
                _("{} will no longer be mentioned when a stream or community is live").format(
                    "@\u200beveryone"
                )
            )
        else:
            await self.db.guild(guild).mention_everyone.set(True)
            await ctx.send(
                _("When a stream or community " "is live, {} will be mentioned.").format(
                    "@\u200beveryone"
                )
            )

    @mention.command(aliases=["here"])
    @commands.guild_only()
    async def online(self, ctx: commands.Context):
        """Toggles here mention"""
        guild = ctx.guild
        current_setting = await self.db.guild(guild).mention_here()
        if current_setting:
            await self.db.guild(guild).mention_here.set(False)
            await ctx.send(_("{} will no longer be mentioned for an alert.").format("@\u200bhere"))
        else:
            await self.db.guild(guild).mention_here.set(True)
            await ctx.send(
                _("When a stream or community " "is live, {} will be mentioned.").format(
                    "@\u200bhere"
                )
            )

    @mention.command()
    @commands.guild_only()
    async def role(self, ctx: commands.Context, *, role: discord.Role):
        """Toggles role mention"""
        current_setting = await self.db.role(role).mention()
        if not role.mentionable:
            await ctx.send("That role is not mentionable!")
            return
        if current_setting:
            await self.db.role(role).mention.set(False)
            await ctx.send(
                _("{} will no longer be mentioned for an alert.").format(
                    "@\u200b{}".format(role.name)
                )
            )
        else:
            await self.db.role(role).mention.set(True)
            await ctx.send(
                _("When a stream or community " "is live, {} will be mentioned." "").format(
                    "@\u200b{}".format(role.name)
                )
            )

    @streamset.command()
    @commands.guild_only()
    async def autodelete(self, ctx: commands.Context, on_off: bool):
        """Toggles automatic deletion of notifications for streams that go offline"""
        await self.db.guild(ctx.guild).autodelete.set(on_off)
        if on_off:
            await ctx.send("The notifications will be deleted once streams go offline.")
        else:
            await ctx.send("Notifications will never be deleted.")

    async def add_or_remove(self, ctx: commands.Context, stream):
        if ctx.channel.id not in stream.channels:
            stream.channels.append(ctx.channel.id)
            if stream not in self.streams:
                self.streams.append(stream)
            await ctx.send(
                _("I'll now send a notification in this channel when {} is live.").format(
                    stream.name
                )
            )
        else:
            stream.channels.remove(ctx.channel.id)
            if not stream.channels:
                self.streams.remove(stream)
            await ctx.send(
                _("I won't send notifications about {} in this channel anymore.").format(
                    stream.name
                )
            )

        await self.save_streams()

    async def add_or_remove_community(self, ctx: commands.Context, community):
        if ctx.channel.id not in community.channels:
            community.channels.append(ctx.channel.id)
            if community not in self.communities:
                self.communities.append(community)
            await ctx.send(
                _(
                    "I'll send a notification in this channel when a "
                    "channel is live in the {} community."
                    ""
                ).format(community.name)
            )
        else:
            community.channels.remove(ctx.channel.id)
            if not community.channels:
                self.communities.remove(community)
            await ctx.send(
                _(
                    "I won't send notifications about channels streaming "
                    "in the {} community in this channel anymore."
                    ""
                ).format(community.name)
            )
        await self.save_communities()

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

    def get_community(self, _class, name):
        for community in self.communities:
            if community.type == _class.__name__ and community.name.lower() == name.lower():
                return community

    async def check_exists(self, stream):
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
            try:
                await self.check_communities()
            except asyncio.CancelledError:
                pass
            await asyncio.sleep(CHECK_DELAY)

    async def check_streams(self):
        for stream in self.streams:
            try:
                embed = await stream.is_online()
            except OfflineStream:
                for message in stream._messages_cache:
                    try:
                        autodelete = await self.db.guild(message.guild).autodelete()
                        if autodelete:
                            await message.delete()
                    except:
                        pass
                stream._messages_cache.clear()
                await self.save_streams()
            except:
                pass
            else:
                if stream._messages_cache:
                    continue
                for channel_id in stream.channels:
                    channel = self.bot.get_channel(channel_id)
                    mention_str = await self._get_mention_str(channel.guild)

                    if mention_str:
                        content = "{}, {} is live!".format(mention_str, stream.name)
                    else:
                        content = "{} is live!".format(stream.name)

                    try:
                        m = await channel.send(content, embed=embed)
                        stream._messages_cache.append(m)
                        await self.save_streams()
                    except:
                        pass

    async def _get_mention_str(self, guild: discord.Guild):
        settings = self.db.guild(guild)
        mentions = []
        if await settings.mention_everyone():
            mentions.append("@everyone")
        if await settings.mention_here():
            mentions.append("@here")
        for role in guild.roles:
            if await self.db.role(role).mention():
                mentions.append(role.mention)
        return " ".join(mentions)

    async def check_communities(self):
        for community in self.communities:
            try:
                stream_list = await community.get_community_streams()
            except CommunityNotFound:
                print(_("The Community {} was not found!").format(community.name))
                continue
            except OfflineCommunity:
                for message in community._messages_cache:
                    try:
                        autodelete = await self.db.guild(message.guild).autodelete()
                        if autodelete:
                            await message.delete()
                    except:
                        pass
                community._messages_cache.clear()
                await self.save_communities()
            except:
                pass
            else:
                for channel in community.channels:
                    chn = self.bot.get_channel(channel)
                    streams = await self.filter_streams(stream_list, chn)
                    emb = await community.make_embed(streams)
                    chn_msg = [m for m in community._messages_cache if m.channel == chn]
                    if not chn_msg:
                        mentions = await self._get_mention_str(chn.guild)
                        if mentions:
                            msg = await chn.send(mentions, embed=emb)
                        else:
                            msg = await chn.send(embed=emb)
                        community._messages_cache.append(msg)
                        await self.save_communities()
                    else:
                        chn_msg = sorted(chn_msg, key=lambda x: x.created_at, reverse=True)[0]
                        community._messages_cache.remove(chn_msg)
                        await chn_msg.edit(embed=emb)
                        community._messages_cache.append(chn_msg)
                        await self.save_communities()

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
            _class = getattr(StreamClasses, raw_stream["type"], None)
            if not _class:
                continue
            raw_msg_cache = raw_stream["messages"]
            raw_stream["_messages_cache"] = []
            for raw_msg in raw_msg_cache:
                chn = self.bot.get_channel(raw_msg["channel"])
                msg = await chn.get_message(raw_msg["message"])
                raw_stream["_messages_cache"].append(msg)
            token = await self.db.tokens.get_raw(_class.__name__, default=None)
            if token is not None:
                raw_stream["token"] = token
            streams.append(_class(**raw_stream))

        return streams

    async def load_communities(self):
        communities = []

        for raw_community in await self.db.communities():
            _class = getattr(StreamClasses, raw_community["type"], None)
            if not _class:
                continue
            raw_msg_cache = raw_community["messages"]
            raw_community["_messages_cache"] = []
            for raw_msg in raw_msg_cache:
                chn = self.bot.get_channel(raw_msg["channel"])
                msg = await chn.get_message(raw_msg["message"])
                raw_community["_messages_cache"].append(msg)
            token = await self.db.tokens.get_raw(_class.__name__, default=None)
            communities.append(_class(token=token, **raw_community))

        # issue 1191 extended resolution: Remove this after suitable period
        # Fast dedupe below
        seen = set()
        seen_add = seen.add
        return [x for x in communities if not (x.name.lower() in seen or seen_add(x.name.lower()))]
        # return communities

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.db.streams.set(raw_streams)

    async def save_communities(self):
        raw_communities = []
        for community in self.communities:
            raw_communities.append(community.export())

        await self.db.communities.set(raw_communities)

    def __unload(self):
        if self.task:
            self.task.cancel()
