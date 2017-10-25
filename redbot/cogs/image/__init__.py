from .image import Image


def setup(bot):
    n = Image(bot)
    bot.add_cog(n)
