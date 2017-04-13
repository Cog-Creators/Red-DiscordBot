import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from datetime import datetime
from collections import deque, defaultdict
from cogs.utils.chat_formatting import escape_mass_mentions, box, pagify
import os
import re
import logging
import asyncio


class Core():
    def __init__(self, bot):
        self.bot = bot


def check_folder():
    pass


def check_file():
    pass


def setup(bot):
    n = Core(bot)
    bot.add_cog(n)
