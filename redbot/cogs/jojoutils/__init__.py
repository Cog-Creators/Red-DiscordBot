from redbot.core.bot import Red
from .jojoutils import JojoUtils


def setup(bot: Red):
    bot.add_cog(JojoUtils(bot))
