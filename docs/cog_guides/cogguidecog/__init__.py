from .cogguidecog import CogGuideCog


async def setup(bot):
    bot.add_cog(CogGuideCog(bot))
