import logging
import asyncio
import contextlib

import discord
from redbot.core import commands, checks, i18n
from redbot.core.utils.chat_formatting import box
from .abc import MixinMeta

log = logging.getLogger("red.mod")
_ = i18n.Translator("Mod", __file__)


# TODO: Empty this to core red.
class MoveToCore(MixinMeta):
    """
    Mixin for things which should really not be in mod, but have not been moved out yet.
    """

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        await self._delete_delay(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # Every message which isn't a command but which
        # starts with a bot prefix is dispatched as a command error
        if not isinstance(error, commands.CommandNotFound):
            await self._delete_delay(ctx)

    async def _delete_delay(self, ctx: commands.Context):
        """Currently used for:
            * delete delay"""
        guild = ctx.guild
        if guild is None:
            return
        message = ctx.message
        delay = await self.settings.guild(guild).delete_delay()

        if delay == -1:
            return

        async def _delete_helper(m):
            with contextlib.suppress(discord.HTTPException):
                await m.delete()
                log.debug("Deleted command msg {}".format(m.id))

        await asyncio.sleep(delay)
        await _delete_helper(message)
