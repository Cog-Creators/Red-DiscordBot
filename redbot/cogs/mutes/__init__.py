from .mutes import Mutes


def setup(bot):
    bot.add_cog(Mutes(bot))
