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
            menu = _("Please select a set of data to import by number.")
            for index, entry in enumerate(
                sorted(resolver.available), 1
            ):
                menu += "\n{}. {}".format(index, entry)
                # TODO: redo the menu logic in a similar fashion as my bansync
                # cog or something logic I was using was convoluted and bad
        else:
            return await ctx.send(
                _("There isn't anything else I know how to convert here."
                  "\nThere might be more things I can convert in the future.")
            )
