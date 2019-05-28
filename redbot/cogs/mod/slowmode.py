import re
from .abc import MixinMeta
from datetime import timedelta
from redbot.core import commands, i18n, checks
from redbot.core.utils.chat_formatting import humanize_timedelta

_ = i18n.Translator("Mod", __file__)


class Slowmode(MixinMeta):
    """
    Commands regarding channel slowmode management.
    """

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def slowmode(self, ctx, interval: str = None):
        """Changes channel's slowmode setting.

        Interval can be anything from 0 seconds to 6 hours.
        You can specify the unit using `s`, `m` or `h` as suffix.
        Use without parameters or set to 0 to disable.
        """
        if interval:
            match = re.match(r"(?i)(\d{1,5})([a-zA-Z])?$", interval)
            if match:
                interval = int(match.group(1))
                if match.group(2) is not None:
                    interval = {"s": 1, "m": 60, "h": 60 * 60}.get(
                        match.group(2).lower(), -1
                    ) * interval
            if not match or not 0 <= interval <= 21600:
                await ctx.send(_("Interval must be between 0 seconds and 6 hours!"))
                return
        else:
            interval = 0
        await ctx.channel.edit(slowmode_delay=interval)
        if interval > 0:
            interval = humanize_timedelta(seconds=interval)
            await ctx.send(_(f"Slowmode interval is now {interval}."))
        else:
            await ctx.send(_("Slowmode has been disabled."))
