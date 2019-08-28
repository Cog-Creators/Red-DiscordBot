from .bank import (
    Bank,
    check_global_setting_guildowner,
    check_global_setting_admin,
    guild_only_check,
)


def setup(bot):
    bot.add_cog(Bank(bot))
