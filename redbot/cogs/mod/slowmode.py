# Standard Library
from datetime import timedelta

# Red Imports
from redbot.core import checks, commands, i18n
from redbot.core.utils.chat_formatting import humanize_timedelta

# Red Relative Imports
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


class Slowmode(MixinMeta):
    """
    Commands regarding channel slowmode management.
    """

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx,
        *,
        interval: commands.TimedeltaConverter(
            minimum=timedelta(seconds=0), maximum=timedelta(hours=6), default_unit="seconds"
        ) = timedelta(seconds=0),
    ):
        """Changes channel's slowmode setting.

        Interval can be anything from 0 seconds to 6 hours.
        Use without parameters to disable.
        """
        seconds = interval.total_seconds()
        await ctx.channel.edit(slowmode_delay=seconds)
        if seconds > 0:
            await ctx.send(
                _("Slowmode interval is now {interval}.").format(
                    interval=humanize_timedelta(timedelta=interval)
                )
            )
        else:
            await ctx.send(_("Slowmode has been disabled."))
