from pathlib import Path
import asyncio

from discord.ext import commands

from redbot.core import checks, RedContext
from redbot.core.bot import Red
from redbot.core.i18n import CogI18n
from redbot.cogs.dataconverter.core_specs import SpecResolver
from redbot.core.utils.chat_formatting import box, pagify

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
        resolver = SpecResolver(Path(v2path.strip()))

        if not resolver.available:
            return await ctx.send(
                _("There don't seem to be any data files I know how to "
                  "handle here. Are you sure you gave me the base "
                  "installation path?")
            )
        while resolver.available:
            menu = _("Please select a set of data to import by number"
                     ", or '-1' to quit")
            for index, entry in enumerate(resolver.available, 1):
                menu += "\n{}. {}".format(index, entry)
            for page in pagify(menu, delims=["\n"]):
                await ctx.send(box(page))

            def pred(m):
                return m.channel == ctx.channel and m.author == ctx.author

            try:
                message = await self.bot.wait_for(
                    'message', check=pred, timeout=60
                )
            except asyncio.TimeoutError:
                return await ctx.send(
                    _('Try this again when you are more ready'))
            else:
                try:
                    message = int(message.content.strip())
                    if message == -1:
                        return await ctx.tick()
                    else:
                        to_conv = resolver.available[message - 1]
                except (ValueError, IndexError):
                    await ctx.send(
                        _("That wasn't a valid choice.")
                    )
                    continue
                else:
                    try:
                        async with ctx.typing():
                            await resolver.convert(self.bot, to_conv)
                    # except AttributeError:
                    #     # TODO: After this has been tested, uncomment
                    except Exception:
                        raise  # TODO: After this has been tested, remove block
                    else:
                        await ctx.send(_("{} converted.").format(to_conv))
        else:
            return await ctx.send(
                _("There isn't anything else I know how to convert here."
                  "\nThere might be more things I can convert in the future.")
            )
