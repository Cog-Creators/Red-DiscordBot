from .audio import Audio


def setup(bot):
    bot.add_cog(Audio(bot))