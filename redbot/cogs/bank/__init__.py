from .bank import Bank, check_global_setting_guildowner, check_global_setting_admin


def setup(bot):
    bot.add_cog(Bank(bot))
