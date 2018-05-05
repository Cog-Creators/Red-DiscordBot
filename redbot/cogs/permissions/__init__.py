from .permissions import Permissions


def setup(bot):
    bot.add_cog(Permissions(bot))
    print("Hey, listen! this isn't ready yet...")
