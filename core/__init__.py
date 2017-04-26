from .owner import Owner

def setup(bot):
    bot.add_cog(Owner(bot))