import discord
from redbot.core import commands, i18n, checks
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)

class Slowmode(MixinMeta):
    """
    Commands regarding channel slowmode management.
    """

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @checks.mod_or_permissions(manage_channels=True)
    async def slowmode(self, ctx, interval: int = 0):
        """Change channel's slowmode setting.

        Interval can be anything from 0 to 21600 seconds.
        Use without parameters or set to 0 to disable.
        """
        if 0 <= interval <= 21600:
            await ctx.send(_("Interval must be between 0 and 21600 seconds!"))
            return
        await ctx.channel.edit(slowmode_delay=interval)
        if interval > 0:
            await ctx.send(_(f"Slowmode interval is now {interval} seconds."))
        else:
            await ctx.send(_("Slowmode has been disabled."))
