from redbot.cogs.audio.cog import Audio
from redbot.core import commands


def setup(bot: commands.Bot):
    bot.add_cog(Audio(bot))
