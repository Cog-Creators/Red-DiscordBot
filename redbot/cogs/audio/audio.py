from discord.ext import commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer
import os
import youtube_dl
import discord


# Just a little experimental audio cog not meant for final release


class Audio:
    """Audio commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def local(self, ctx, *, filename: str):
        """Play mp3"""
        if ctx.author.voice is None:
            await ctx.send("Join a voice channel first!")
            return

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.voice_client.disconnect()
        path = os.path.join("cogs", "audio", "songs", filename + ".mp3")
        if not os.path.isfile(path):
            await ctx.send("Let's play a file that exists pls")
            return
        player = PCMVolumeTransformer(FFmpegPCMAudio(path), volume=1)
        voice = await ctx.author.voice.channel.connect()
        voice.play(player)
        await ctx.send("{} is playing a song...".format(ctx.author))

    @commands.command()
    async def play(self, ctx, url: str):
        """Play youtube url"""
        url = url.strip("<").strip(">")
        if ctx.author.voice is None:
            await ctx.send("Join a voice channel first!")
            return
        elif "youtube.com" not in url.lower():
            await ctx.send("Youtube links pls")
            return

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.voice_client.disconnect()
        yt = YoutubeSource(url)
        player = PCMVolumeTransformer(yt, volume=1)
        voice = await ctx.author.voice.channel.connect()
        voice.play(player)
        await ctx.send("{} is playing a song...".format(ctx.author))

    @commands.command()
    async def stop(self, ctx):
        """Stops the music and disconnects"""
        if ctx.voice_client:
            ctx.voice_client.source.cleanup()
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("I'm not even connected to a voice channel!", delete_after=2)
        await ctx.message.delete()

    @commands.command()
    async def pause(self, ctx):
        """Pauses the music"""
        if ctx.voice_client:
            ctx.voice_client.pause()
            await ctx.send("👌", delete_after=2)
        else:
            await ctx.send("I'm not even connected to a voice channel!", delete_after=2)
        await ctx.message.delete()

    @commands.command()
    async def resume(self, ctx):
        """Resumes the music"""
        if ctx.voice_client:
            ctx.voice_client.resume()
            await ctx.send("👌", delete_after=2)
        else:
            await ctx.send("I'm not even connected to a voice channel!", delete_after=2)
        await ctx.message.delete()

    @commands.command(hidden=True)
    async def volume(self, ctx, n: float):
        """Sets the volume"""
        if ctx.voice_client:
            ctx.voice_client.source.volume = n
            await ctx.send("Volume set.", delete_after=2)
        else:
            await ctx.send("I'm not even connected to a voice channel!", delete_after=2)
        await ctx.message.delete()

    def __unload(self):
        for vc in self.bot.voice_clients:
            if vc.source:
                vc.source.cleanup()
            self.bot.loop.create_task(vc.disconnect())


class YoutubeSource(discord.FFmpegPCMAudio):
    def __init__(self, url):
        opts = {
            'format': 'webm[abr>0]/bestaudio/best',
            'prefer_ffmpeg': True,
            'quiet': True
        }
        ytdl = youtube_dl.YoutubeDL(opts)
        self.info = ytdl.extract_info(url, download=False)
        super().__init__(self.info['url'])