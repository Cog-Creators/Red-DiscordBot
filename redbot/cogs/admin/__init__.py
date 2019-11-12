# -*- coding: utf-8 -*-
# Red Relative Imports
from .admin import Admin


def setup(bot):
    bot.add_cog(Admin())
