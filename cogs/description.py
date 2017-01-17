from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import description as old_description

JSON = "data/description.json"


class Description:

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(JSON)
        # Restore on startup/load
        d = self.settings.get('description', None)
        if d:
            self.bot.description = d

    @commands.command()
    @checks.is_owner()
    async def description(self, *, description: str = None):
        """Sets the bot's description text"""
        if description:
            self.settings['description'] = description
            await self.bot.say('Bot description set.')
        else:
            description = old_description
            self.settings['description'] = None
            await self.bot.say('Default description restored.')

        self.bot.description = description
        dataIO.save_json(JSON, self.settings)


def check_files(bot):
    if not dataIO.is_valid_json(JSON):
        print("Creating default description.json...")
        dataIO.save_json(JSON, {})


def setup(bot):
    check_files(bot)
    n = Description(bot)
    bot.add_cog(n)
