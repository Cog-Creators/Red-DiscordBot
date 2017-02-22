import os
import random
from typing import List

import discord
from discord.ext import commands

from .utils.dataIO import dataIO
from .utils import checks, chat_formatting as cf


default_settings = {
    "next_index": 1,
    "quotes": {}
}


class Quotes:

    """Stores and shows quotes."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings_path = "data/quotes/settings.json"
        self.settings = dataIO.load_json(self.settings_path)

    def list_quotes(self, server: discord.Server) -> List[str]:
        tups = [(int(k), v)
                for (k, v) in self.settings[server.id]["quotes"].items()]
        tups.sort(key=lambda x: x[0])
        return ["{}. {}".format(n, q) for (n, q) in tups]

    @commands.command(pass_context=True, no_pm=True, name="addquote")
    async def _addquote(self, ctx: commands.Context, *,
                        new_quote: str):
        """Adds a new quote."""

        await self.bot.type()
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            dataIO.save_json(self.settings_path, self.settings)

        idx = self.settings[server.id]["next_index"]
        self.settings[server.id]["quotes"][str(idx)] = new_quote
        self.settings[server.id]["next_index"] += 1
        dataIO.save_json(self.settings_path, self.settings)

        await self.bot.reply(
            cf.info("Quote added as number {}.".format(idx)))

    @commands.command(pass_context=True, no_pm=True, name="delquote")
    async def _delquote(self, ctx: commands.Context, number: str):
        """Deletes an existing quote."""

        await self.bot.type()
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings

        try:
            int(number)
        except (ValueError, TypeError):
            await self.bot.reply(cf.error(
                "Please provide a quote number to delete."
                " Try `{}allquotes` for a list.".format(ctx.prefix)))
            return

        try:
            del self.settings[server.id]["quotes"][number]
        except KeyError:
            await self.bot.reply(cf.error(
                "A quote with that number cannot be found."
                " Try `{}allquotes` for a list.".format(ctx.prefix)))
            return

        dataIO.save_json(self.settings_path, self.settings)

        await self.bot.reply(
            cf.info("Quote number {} deleted.".format(number)))

    @commands.command(pass_context=True, no_pm=False, name="allquotes")
    async def _allquotes(self, ctx: commands.Context):
        """Sends all quotes in a PM."""

        await self.bot.type()
        server = ctx.message.server

        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            dataIO.save_json(self.settings_path, self.settings)

        if len(self.settings[server.id]["quotes"]) == 0:
            await self.bot.reply(cf.warning(
                "There are no saved quotes."
                " Use `{}addquote` to add one.".format(ctx.prefix)))
            return

        strbuffer = self.list_quotes(server)
        mess = "```"
        for line in strbuffer:
            if len(mess) + len(line) + 4 < 2000:
                mess += "\n" + line
            else:
                mess += "```"
                await self.bot.whisper(mess)
                mess = "```" + line
        if mess != "":
            mess += "```"
            await self.bot.whisper(mess)

        await self.bot.reply("Check your PMs!")

    @commands.command(pass_context=True, no_pm=True, name="quote")
    async def _quote(self, ctx: commands.Context, *, number: str=None):
        """Sends a random quote."""

        await self.bot.type()
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = default_settings
            dataIO.save_json(self.settings_path, self.settings)

        if len(self.settings[server.id]["quotes"]) == 0:
            await self.bot.reply(cf.warning(
                "There are no saved quotes."
                " Use `{}addquote` to add one.".format(ctx.prefix)))
            return

        if number:
            try:
                int(number)
            except (ValueError, TypeError):
                await self.bot.reply(cf.warning(
                    "Please provide a number to get that specific quote."
                    " If you are trying to add a quote, use `{}addquote`."
                    .format(ctx.prefix)))
                return

            try:
                await self.bot.say(self.settings[server.id]["quotes"][number])
                return
            except KeyError:
                await self.bot.reply(cf.warning(
                    "A quote with that number cannot be found."
                    " Try `{}allquotes` for a list.".format(ctx.prefix)))
                return

        await self.bot.say(random.choice(
            list(self.settings[server.id]["quotes"].values())))


def check_folders():
    if not os.path.exists("data/quotes"):
        print("Creating data/quotes directory...")
        os.makedirs("data/quotes")


def check_files():
    f = "data/quotes/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/quotes/settings.json...")
        dataIO.save_json(f, {})


def setup(bot: commands.Bot):
    check_folders()
    check_files()
    bot.add_cog(Quotes(bot))
