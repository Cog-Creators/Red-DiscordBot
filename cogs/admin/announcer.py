import asyncio
from typing import MutableMapping

import discord
from discord.ext import commands


class Announcer:
    def __init__(self, ctx: commands.Context,
                 message: str,
                 config=None):
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
            asyncio.ensure_future(self.announcer(), loop=ctx.bot.loop)

    def cancel(self):
        """
        Cancels a running announcement.
        :return:
        """
        self.active = False

    def _get_announce_channel(self, guild: discord.Guild) -> discord.TextChannel:
        channel_id = self.config.guild(g).announce_channel()
        channel = None

        if channel_id is not None:
            channel = self.ctx.bot.get_channel(channel_id=int(channel_id))

        if channel is None:
            channel = g

        return channel

    async def announcer(self):
        guild_list = self.ctx.bot.guilds
        bot_owner = (await self.ctx.bot.application_info()).owner
        for g in guild_list:
            if not self.active:
                return

            if self.config.guild(g).announce_ignore():
                continue

            channel = self._get_announce_channel(g)

            try:
                await channel.send(self.message)
            except discord.Forbidden:
                await bot_owner.send("I could not announce to guild: {}".format(
                                         g.id
                                     ))
            await asyncio.sleep(0.5)

        self.active = False

