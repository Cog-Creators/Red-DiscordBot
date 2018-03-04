from pathlib import Path

from discord.ext import commands

from redbot.core import checks, RedContext
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.cogs.dataconverter.core_specs import SpecResolver

_ = CogI18n('DataConverter', __file__)


class DataConverter:
    """
    Cog for importing Red v2 Data
    """

    def __init__(self, bot: Red):
        self.bot = bot

    @checks.is_owner()
    @commands.command(name="convertdata")
    async def dataconversioncommand(self, ctx: RedContext, v2path: str):
        """
        Interactive prompt for importing data from Red v2

        Takes the path where the v2 install is
        """
        resolver = SpecResolver(Path(v2path))

        if not resolver.available:
            return await ctx.send(
                _("There don't seem to be any data files I know how to "
                  "handle here. Are you sure you gave me the base "
                  "installation path?")
            )
        while resolver.available:
            pass  # TODO
            # interactive logic from resolver available
            # should call `await resolver.convert(key)`
            # where key is in resolver.availble and chosen by user
            # use a break if an exit is asked for
        else:
            pass  # TODO
            # Should inform the user nothing else is available to be converted
