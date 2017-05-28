from discord.ext import commands
from core.config import Config
from .streams import TwitchStream, HitboxStream, BeamStream, PicartoStream
from .errors import OfflineStream, StreamNotFound, APIError, InvalidCredentials
from . import streams as StreamClasses
import asyncio

CHECK_DELAY = 60


class Streams:
    def __init__(self, bot):
        self.db = Config.get_conf(self, 26262626, force_registration=True)

        self.db.register_global(
            tokens={},
            streams=[]
        )

        self.db.register_guild(
            settings={}
        )

        self.streams = self.load_streams()
        self.task = bot.loop.create_task(self._stream_alerts())
        self.bot = bot

    @commands.command()
    async def twitch(self, ctx, channel_name: str):
        """Checks if a Twitch channel is streaming"""
        token = self.db.tokens().get(TwitchStream.__name__)
        stream = TwitchStream(name=channel_name,
                              token=token)
        await self.check_online(ctx, stream)

    @commands.command()
    async def hitbox(self, ctx, channel_name: str):
        """Checks if a Hitbox channel is streaming"""
        stream = HitboxStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def beam(self, ctx, channel_name: str):
        """Checks if a beam.pro channel is streaming"""
        stream = BeamStream(name=channel_name)
        await self.check_online(ctx, stream)

    @commands.command()
    async def picarto(self, ctx, channel_name: str):
        """Checks if a Picarto channel is streaming"""
        stream = PicartoStream(name=channel_name)
        await self.check_online(ctx, stream)

    async def check_online(self, ctx, stream):
        try:
            embed = await stream.is_online()
        except OfflineStream:
            await ctx.send("The stream is offline.")
        except StreamNotFound:
            await ctx.send("The channel doesn't seem to exist.")
        except InvalidCredentials:
            await ctx.send("Invalid twitch token.")
        except APIError:
            await ctx.send("Error contacting the API.")
        else:
            await ctx.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    async def streamalert(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.bot.send_cmd_help(ctx)

    @streamalert.command(name="twitch")
    async def twitch_alert(self, ctx, channel_name: str):
        """Sets a Twitch stream alert notification in the channel"""
        await self.stream_alert(ctx, TwitchStream, channel_name)

    @streamalert.command(name="hitbox")
    async def hitbox_alert(self, ctx, channel_name: str):
        """Sets a Hitbox stream alert notification in the channel"""
        await self.stream_alert(ctx, HitboxStream, channel_name)

    @streamalert.command(name="beam")
    async def beam_alert(self, ctx, channel_name: str):
        """Sets a beam.pro stream alert notification in the channel"""
        await self.stream_alert(ctx, BeamStream, channel_name)

    @streamalert.command(name="picarto")
    async def picarto_alert(self, ctx, channel_name: str):
        """Sets a Picarto stream alert notification in the channel"""
        await self.stream_alert(ctx, PicartoStream, channel_name)

    @streamalert.command(name="stop")
    async def streamalert_stop(self, ctx, all: bool):
        """Stops all stream notifications in the channel

        Adding 'yes' will stops all notifications in the server"""
        await self.stream_alert(ctx, PicartoStream, channel_name)

    async def stream_alert(self, ctx, _class, channel_name):
        stream = self.get_stream(_class, channel_name)
        if not stream:
            token = self.db.tokens().get(_class.__name__)
            stream = _class(name=channel_name,
                            token=token)
        if await self.check_exists(stream):
            await self.add_or_remove(ctx, stream)
        else:
            await ctx.send("That channel doesn't seem to exist.")

    @commands.group()
    async def streamset(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.bot.send_cmd_help(ctx)

    @streamset.command()
    async def twitchtoken(self, ctx, token: str):
        tokens = self.db.tokens()
        tokens["TwitchStream"] = token
        await self.db.set("tokens", tokens)
        await ctx.send("Twitch token set.")

    @streamset.command()
    @commands.guild_only()
    async def autodelete(self, ctx, on_off: bool):
        settings = self.db.settings()
        if str(ctx.guild.id) not in settings:
            settings[str(ctx.guild.id)] = {}
        settings[str(ctx.guild.id)]["autodelete"] = on_off
        await self.db.set("settings", settings)

        if on_off:
            await ctx.send("The notifications will be deleted once "
                           "streams go offline.")
        else:
            await ctx.send("Notifications will never be deleted.")

    async def add_or_remove(self, ctx, stream):
        if ctx.channel.id not in stream.channels:
            stream.channels.append(ctx.channel.id)
            if stream not in self.streams:
                self.streams.append(stream)
            await ctx.send("I'll send a notification in this channel when {} "
                           "is online.".format(stream.name))
        else:
            stream.channels.remove(ctx.channel.id)
            if not stream.channels:
                self.streams.remove(stream)
            await ctx.send("I won't send notifications about {} in this "
                           "channel anymore.".format(stream.name))
        await self.save_streams()

    def get_stream(self, _class, name):
        for stream in self.streams:
            if isinstance(stream, _class) and stream.name == name:
                return stream

    async def check_exists(self, stream):
        try:
            await stream.is_online()
        except OfflineStream:
            pass
        except:
            return False
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
            try:
                embed = await stream.is_online()
            except OfflineStream:
                for message in stream._messages_cache:
                    try:
                        await message.delete()
                    except:
                        pass
                stream._messages_cache.clear()
            except:
                pass
            else:
                if stream._messages_cache:
                    continue
                for channel_id in stream.channels:
                    channel = self.bot.get_channel(channel_id)
                    try:
                        m = await channel.send("%s is online!" % stream.name,
                                               embed=embed)
                        stream._messages_cache.append(m)
                    except:
                        pass

    def load_streams(self):
        streams = []

        for raw_stream in self.db.streams():
            _class = getattr(StreamClasses, raw_stream["type"], None)
            if not _class:
                continue

            token = self.db.tokens().get(_class.__name__)
            streams.append(_class(token=token, **raw_stream))

        return streams

    async def save_streams(self):
        raw_streams = []
        for stream in self.streams:
            raw_streams.append(stream.export())

        await self.db.set("streams", raw_streams)

    def __unload(self):
        self.task.cancel()
