from .bank import Bank, check_global_setting_guildowner, check_global_setting_admin


async def setup(bot):
    await bot.add_cog(Bank(bot))
