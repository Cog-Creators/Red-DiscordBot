import discord
from discord.ext import commands
import aiohttp
import asyncio
import math

numbs = {
    0: "0⃣",
    1: "1⃣",
    2: "2⃣",
    3: "3⃣",
    4: "4⃣",
    5: "5⃣",
    6: "6⃣",
    7: "7⃣",
    8: "8⃣",
    9: "9⃣",
    10: "🔟",
    "next": "➡",
    "back": "⬅",
    "yes": "✅",
    "no": "❌"
}

__author__ = "Awoonar Dust#7332"


def default_check(reaction, user):
    if user.bot:
        return False
    if reaction.emoji in numbs.values():
        return True
    else:
        return False


async def _timed_out(self, ctx):
    return await self.bot.say("Menu has expired.")


class Menu:
    def __init__(self, bot):
        self.bot = bot
        self.current_menus = {}
        self.timeout = 15

    async def _show_page(self, message: discord.Message, pages: list, count):
        if count != 0:
            await self.bot.add_reaction(message, str(numbs['back']))
        for idx, i in enumerate(pages[count], 1):
            await self.bot.add_reaction(message, str(numbs[idx]))
        if count < len(pages) - 1:
            await self.bot.add_reaction(message, str(numbs['next']))

    async def confirm_menu(self, ctx, choice, message=""):
        if message == "":
            message = "```Are you sure?```"

        sent_msg = await self.bot.say(message)

        await self.bot.add_reaction(sent_msg, str(numbs['yes']))
        await self.bot.add_reaction(sent_msg, str(numbs['no']))

        react = await self.bot.wait_for_reaction(
            message=sent_msg,
            check=default_check,
            user=ctx.message.author,
            timeout=self.timeout)

        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]

        if react == "no":
            return False
        return choice

    async def number_menu(self, ctx,
                          message: str, choices: list,
                          page=0, autodelete=True,
                          confirm=False):

        if message == "" or choices == []:
            return

        pages = [choices[x:x + 10] for x in range(0, len(choices), 10)]

        choice_msg = ""

        for idx, x in enumerate(pages[page], 1):
            choice_msg += "{0} - {1}\n".format(str(idx), str(x))

        sent_msg = await self.bot.say("```\n{0}\n{1}```".format(message, choice_msg))

        await self._show_page(sent_msg, pages, page)

        self.current_menus[ctx.message.author] = [sent_msg, pages, page]

        react = await self.bot.wait_for_reaction(
            message=sent_msg, check=default_check,
            user=ctx.message.author, timeout=self.timeout)

        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]

        if react == "next":
            await self.bot.delete_message(sent_msg)
            return await self.number_menu(
                ctx, message, choices, page=page + 1)
        if react == "back":
            await self.bot.delete_message(sent_msg)
            return await self.number_menu(
                ctx, message, choices, page=page - 1)

        if autodelete:
            await self.bot.delete_message(sent_msg)

        if confirm:
            return await self.confirm_menu(ctx, react)

        if react is None:
            return None
        else:
            return (page * 10 + react)

    async def _custom_menu(
            self, ctx,
            message: str, choices,
            timeout=15, is_open=False,
            on_timeout=_timed_out,
            check=default_check,
            custom_code=None):
        """A custom menu creator
Arguements:
    ctx(obvious)
    message- a pre-formatted(as in it will be straight up displayed) message
    choices- the list of choices you want to use
Optional arguements:
    timeout- how long the menu will remain open in seconds. Defaults to 15 seconds
    on_timeout- code to run when the timeout is reached. Defaults to saying "Menu has expired"
    check- passed to wait_for_reaction (I strongly recommend returning False if the user is a bot). Defaults to checking if the user is a bot
    custom_code- any code you just want to run(idk what you'd want with it) in a function
    is_open- whether or not the menu should only be usable by the use who called the command. Defaults to calling user only

Returns:
    None if the menu timed out
    Reaction + User if successful
        """
        sent_msg = await self.bot.send_message(ctx.message.channel, message)

        for idx, x in enumerate(choices, 1):
            await self.bot.add_reaction(sent_msg, str(numbs[idx]))
        self.current_menus[ctx.message.author] = [sent_msg, choices]

        react = None

        if is_open:
            react = await self.bot.wait_for_reaction(message=sent_msg, check=check, timeout=timeout)
        else:
            react = await self.bot.wait_for_reaction(message=sent_msg, check=check, user=ctx.message.author, timeout=timeout)

        if custom_code is not None:
            custom_code()

        if react is None:
            return None
        else:
            return react

    @commands.command(pass_context=True)
    async def menu(self, ctx, message: str, choices: str):
        choices = choices.split(',')
        react = await self.number_menu(ctx, message, choices, autodelete=True, confirm=True)
        if react is False:
            return await self.bot.say("Menu cancelled")
        await self.bot.say("{0.message.author} pressed {1}".format(ctx, react))


def setup(bot):
    n = Menu(bot)
    bot.add_cog(n)
