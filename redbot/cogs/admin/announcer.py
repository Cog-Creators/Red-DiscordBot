import asyncio

import discord
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_list, inline

_ = Translator("Announcer", __file__)


class Announcer:
    def __init__(self, ctx: commands.Context, message: str, config=None):
        """
        :param ctx:
        :param message:
        :param config: Used to determine channel overrides
        """
        self.ctx = ctx
        self.message = message
        self.config = config

        self.active = None

    def start(self):
        """
        Starts an announcement.
        :return:
        """
        if self.active is None:
            self.active = True
            self.ctx.bot.loop.create_task(self.announcer())

    def cancel(self):
        """
        Cancels a running announcement.
        :return:
        """
        self.active = False

    async def _get_announce_channel(self, guild: discord.Guild) -> discord.TextChannel:
        channel_id = await self.config.guild(guild).announce_channel()
        channel = None

        if channel_id is not None:
            channel = guild.get_channel(channel_id)

        if channel is None:
            channel = guild.system_channel

        if channel is None:
            channel = guild.text_channels[0]

        return channel

    async def announcer(self):
        guild_list = self.ctx.bot.guilds
        failed = []
        for g in guild_list:
            if not self.active:
                return

            if await self.config.guild(g).announce_ignore():
                continue

            channel = await self._get_announce_channel(g)

            try:
                await channel.send(self.message)
            except discord.Forbidden:
                failed.append(str(g.id))
            await asyncio.sleep(0.5)

        if failed:
            msg = (
                _("I could not announce to the following server: ")
                if len(failed) == 1
                else _("I could not announce to the following servers: ")
            )
            msg += humanize_list(tuple(map(inline, failed)))
            await self.ctx.bot.send_to_owners(msg)
        self.active = False
