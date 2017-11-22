import asyncio
from copy import deepcopy
import os
import os.path

import aiohttp
import discord
from discord.ext import commands

from .utils.dataIO import dataIO
from .utils import checks, chat_formatting as cf


default_settings = {
    "join_on": False,
    "leave_on": False
}


class CustomJoinLeave:

    """Play a sound byte when you join or leave a channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.audio_players = {}
        self.sound_base = "data/customjoinleave"
        self.settings_path = "data/customjoinleave/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    def voice_channel_full(self, voice_channel: discord.Channel) -> bool:
        return (voice_channel.user_limit != 0 and
                len(voice_channel.voice_members) >= voice_channel.user_limit)

    def voice_connected(self, server: discord.Server) -> bool:
        return self.bot.is_voice_connected(server)

    def voice_client(self, server: discord.Server) -> discord.VoiceClient:
        return self.bot.voice_client_in(server)

    async def _leave_voice_channel(self, server: discord.Server):
        if not self.voice_connected(server):
            return
        voice_client = self.voice_client(server)

        if server.id in self.audio_players:
            self.audio_players[server.id].stop()
        await voice_client.disconnect()

    async def wait_for_disconnect(self, server: discord.Server):
        while not self.audio_players[server.id].is_done():
            await asyncio.sleep(0.01)
        await self._leave_voice_channel(server)

    async def sound_init(self, server: discord.Server, path: str):
        options = "-filter \"volume=volume=0.15\""
        voice_client = self.voice_client(server)
        self.audio_players[server.id] = voice_client.create_ffmpeg_player(
            path, options=options)

    async def sound_play(self, server: discord.Server,
                         channel: discord.Channel, p: str):
        if self.voice_channel_full(channel):
            return

        if not channel.is_private:
            if self.voice_connected(server):
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)
            else:
                await self.bot.join_voice_channel(channel)
                if server.id not in self.audio_players:
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)
                else:
                    if self.audio_players[server.id].is_playing():
                        self.audio_players[server.id].stop()
                    await self.sound_init(server, p)
                    self.audio_players[server.id].start()
                    await self.wait_for_disconnect(server)

    @commands.group(pass_context=True, no_pm=True, name="joinleaveset")
    async def _joinleaveset(self, ctx: commands.Context):
        """Sets custom join/leave settings."""

        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = deepcopy(default_settings)
            dataIO.save_json(self.settings_path, self.settings)
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_joinleaveset.command(pass_context=True, no_pm=True, name="togglejoin")
    @checks.admin_or_permissions(manage_server=True)
    async def _togglejoin(self, ctx: commands.Context):
        """Toggles custom join sounds on/off."""

        await self.bot.type()

        server = ctx.message.server
        self.settings[server.id][
            "join_on"] = not self.settings[server.id]["join_on"]
        if self.settings[server.id]["join_on"]:
            await self.bot.reply(
                cf.info("Custom join sounds are now enabled."))
        else:
            await self.bot.reply(
                cf.info("Custom join sounds are now disabled."))
        dataIO.save_json(self.settings_path, self.settings)

    @_joinleaveset.command(pass_context=True, no_pm=True, name="toggleleave")
    @checks.admin_or_permissions(manage_server=True)
    async def _toggleleave(self, ctx: commands.Context):
        """Toggles custom join sounds on/off."""

        await self.bot.type()

        server = ctx.message.server
        self.settings[server.id]["leave_on"] = not self.settings[
            server.id]["leave_on"]
        if self.settings[server.id]["leave_on"]:
            await self.bot.reply(
                cf.info("Custom leave sounds are now enabled."))
        else:
            await self.bot.reply(
                cf.info("Custom leave sounds are now disabled."))
        dataIO.save_json(self.settings_path, self.settings)

    @commands.command(pass_context=True, no_pm=True, name="setjoinsound")
    @commands.has_role("custom sound")
    async def _setjoinsound(self, ctx: commands.Context,
                            link: str=None):
        """Sets the join sound for the calling user."""

        await self._set_sound(ctx, link, "join", ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True, name="setleavesound")
    @commands.has_role("custom sound")
    async def _setleavesound(self, ctx: commands.Context,
                             link: str=None):
        """Sets the leave sound for the calling user."""

        await self._set_sound(ctx, link, "leave", ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True, name="setjoinsoundfor")
    @checks.admin_or_permissions(Administrator=True)
    async def _setjoinsoundfor(self, ctx: commands.Context,
                               user: discord.User, link: str=None):
        """Sets the join sound for the given user."""

        await self._set_sound(ctx, link, "join", user.id)

    @commands.command(pass_context=True, no_pm=True, name="setleavesoundfor")
    @checks.admin_or_permissions(Administrator=True)
    async def _setleavesoundfor(self, ctx: commands.Context,
                                user: discord.User, link: str=None):
        """Sets the leave sound for the given user."""

        await self._set_sound(ctx, link, "leave", user.id)

    async def _set_sound(self, ctx: commands.Context, link: str,
                         action: str, userid: str):
        await self.bot.type()

        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = deepcopy(default_settings)
            dataIO.save_json(self.settings_path, self.settings)

        attach = ctx.message.attachments
        if len(attach) > 1 or (attach and link):
            await self.bot.reply(cf.error("Please only provide one file."))
            return

        url = ""
        if attach:
            url = attach[0]["url"]
        elif link:
            url = link
        else:
            await self.bot.reply(cf.error(
                "You must provide either a Discord "
                "attachment or a direct link to a sound."))
            return

        path = "{}/{}".format(self.sound_base, server.id)
        if not os.path.exists(path):
            os.makedirs(path)

        path = "{}/{}/{}".format(self.sound_base, server.id, userid)
        if not os.path.exists(path):
            os.makedirs(path)

        path += "/" + action
        if os.path.exists(path):
            await self.bot.reply(cf.question(
                "There is already a custom {} sound. "
                "Do you want to replace it? (yes/no)".format(action)))
            answer = await self.bot.wait_for_message(timeout=15,
                                                     author=ctx.message.author)

            if answer is None or answer.content.lower().strip() != "yes":
                await self.bot.reply(
                    "{} sound not replaced.".format(action.capitalize()))
                return

            os.remove(path)

        async with aiohttp.get(url) as nwsnd:
            f = open(path, "wb")
            f.write(await nwsnd.read())
            f.close
            await self.bot.reply("{} sound added.".format(action.capitalize()))

    @commands.command(pass_context=True, no_pm=True, name="deljoinsound")
    async def _deljoinsound(self, ctx: commands.Context):
        """Deletes the join sound for the calling user."""

        await self._del_sound(ctx, "join", ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True, name="delleavesound")
    async def _delleavesound(self, ctx: commands.Context):
        """Deletes the leave sound for the calling user."""

        await self._del_sound(ctx, "leave", ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True, name="deljoinsoundfor")
    @checks.admin_or_permissions(Administrator=True)
    async def _deljoinsoundfor(self, ctx: commands.Context,
                               user: discord.User):
        """Deletes the join sound for the given user."""

        await self._del_sound(ctx, "join", user.id)

    @commands.command(pass_context=True, no_pm=True, name="delleavesoundfor")
    @checks.admin_or_permissions(Administrator=True)
    async def _delleavesoundfor(self, ctx: commands.Context,
                                user: discord.User):
        """Deletes the leave sound for the given user."""

        await self._del_sound(ctx, "leave", user.id)

    async def _del_sound(self, ctx, action, userid):
        await self.bot.type()

        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = deepcopy(default_settings)
            dataIO.save_json(self.settings_path, self.settings)

        path = "{}/{}".format(self.sound_base, server.id)
        if not os.path.exists(path):
            await self.bot.reply(cf.warning(
                "There is not a custom {} sound.".format(action)))
            return

        path = "{}/{}/{}".format(self.sound_base, server.id, userid)
        if not os.path.exists(path):
            await self.bot.reply(cf.warning(
                "There is not a custom {} sound.".format(action)))
            return

        path += "/" + action
        if not os.path.exists(path):
            await self.bot.reply(cf.warning(
                "There is not a custom {} sound.".format(action)))
            return

        os.remove(path)
        await self.bot.reply(cf.info(
            "{} sound deleted.".format(action.capitalize())))

    async def voice_state_update(self, before: discord.Member,
                                 after: discord.Member):
        bserver = before.server
        aserver = after.server

        bvchan = before.voice.voice_channel
        avchan = after.voice.voice_channel

        sfx_cog = self.bot.get_cog("Sfx")

        if bserver.id not in self.settings:
            self.settings[bserver.id] = deepcopy(default_settings)
            dataIO.save_json(self.settings_path, self.settings)

        if aserver.id not in self.settings:
            self.settings[aserver.id] = deepcopy(default_settings)
            dataIO.save_json(self.settings_path, self.settings)

        if bvchan != avchan:
            # went from no channel to a channel
            if (bvchan is None and avchan is not None and
                    self.settings[aserver.id]["join_on"] and
                    avchan != aserver.afk_channel and
                    avchan.permissions_for(
                        bserver.me).connect):
                path = "{}/{}/{}/join".format(self.sound_base,
                                              aserver.id, after.id)
                if os.path.exists(path):
                    if sfx_cog is not None:
                        if not sfx_cog.enqueue_sfx(avchan, path, vol=15):
                            await self.sound_play(aserver, avchan, path)
                    else:
                        await self.sound_play(aserver, avchan, path)

            # went from one channel to another
            elif bvchan is not None and avchan is not None:
                if (self.settings[bserver.id]["leave_on"] and
                        bvchan != bserver.afk_channel and
                        bvchan.permissions_for(
                            bserver.me).connect):
                    path = "{}/{}/{}/leave".format(
                        self.sound_base, bserver.id, before.id)
                    if os.path.exists(path):
                        if sfx_cog is not None:
                            if not sfx_cog.enqueue_sfx(bvchan, path, vol=15):
                                await self.sound_play(bserver, bvchan, path)
                        else:
                            await self.sound_play(bserver, bvchan, path)
                if (self.settings[aserver.id]["join_on"] and
                        avchan != aserver.afk_channel and
                        avchan.permissions_for(
                            bserver.me).connect):
                    path = "{}/{}/{}/join".format(self.sound_base,
                                                  aserver.id, after.id)
                    if os.path.exists(path):
                        if sfx_cog is not None:
                            if not sfx_cog.enqueue_sfx(avchan, path, vol=15):
                                await self.sound_play(aserver, avchan, path)
                        else:
                            await self.sound_play(aserver, avchan, path)

            # went from a channel to no channel
            elif (bvchan is not None and
                  avchan is None and
                  self.settings[bserver.id]["leave_on"] and
                  bvchan != bserver.afk_channel and
                  bvchan.permissions_for(
                    bserver.me).connect):
                path = "{}/{}/{}/leave".format(self.sound_base,
                                               bserver.id, before.id)
                if os.path.exists(path):
                    if sfx_cog is not None:
                        if not sfx_cog.enqueue_sfx(bvchan, path, vol=15):
                            await self.sound_play(bserver, bvchan, path)
                    else:
                        await self.sound_play(bserver, bvchan, path)


def check_folders():
    if not os.path.exists("data/customjoinleave"):
        print("Creating data/customjoinleave directory...")
        os.makedirs("data/customjoinleave")


def check_files():
    f = "data/customjoinleave/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/customjoinleave/settings.json...")
        dataIO.save_json(f, {})


def setup(bot: commands.Bot):
    check_folders()
    check_files()
    n = CustomJoinLeave(bot)
    bot.add_listener(n.voice_state_update, "on_voice_state_update")

    bot.add_cog(n)
