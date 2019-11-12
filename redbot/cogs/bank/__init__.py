# -*- coding: utf-8 -*-
# Red Relative Imports
from .bank import Bank, check_global_setting_admin, check_global_setting_guildowner


def setup(bot):
    bot.add_cog(Bank(bot))
