from .alias import Alias
from discord.ext import commands


def setup(bot: commands.Bot):
    bot.add_cog(Alias(bot))
