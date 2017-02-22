from discord.ext import commands
from __main__ import send_cmd_help
import aiohttp
import json

class Transformice:
    """Get user/tribe info from Transformice.com"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="tfm", pass_context=True, invoke_without_command=True)
    async def tfm(self, ctx):
        """Get Transformice Stats"""
        await send_cmd_help(ctx)

    @tfm.command(pass_context=True)
    async def mouse(self, ctx, *, user):
        """Get Transformice mouse info"""

        try:
            link = "http://api.micetigri.fr/json/player/{}".format(user)
            async with aiohttp.get(link) as m:
                result = await m.json()
                name = result['name']
                mouseid = result['id']
                tribe = result['tribe']
                title = result['title']
                date = result['registration']
                exp = result['experience']
                msg = "Transformice Username Info:\n"
                msg += "**Mouse:** {}\n".format(name)
                msg += "**Id:** {}\n".format(mouseid)
                msg += "**Tribe:** {}\n".format(tribe)
                msg += "**Title:** {}\n".format(title)
                msg += "**Join Date:** {}\n".format(date)
                msg += "**Experience:** {}\n".format(exp)
                await self.bot.say(msg)
        except ValueError:
                await self.bot.say("Please provide a valid transformice username! Try registering at transformice.com")

    @tfm.command(pass_context=True)
    async def tribe(self, ctx, *, tribe):
        """Get Transformice tribe info."""

        try:
            link = "http://api.micetigri.fr/json/tribe/{}".format(tribe)
            async with aiohttp.get(link) as t:
                result = await t.json()
                tribe = result['name']
                tribeid = result['id']
                join = result['forum_recruitment']
                members = ", ".join(result['members'])
                msg = "Transformice Tribe Info:\n"
                msg += "**Tribe:** {}\n".format(tribe)
                msg += "**Id:** {}\n".format(tribeid)
                msg += "**Members:** {}\n".format(members)
                msg += "**Openings:** {}\n".format(join)
                await self.bot.say(msg)
        except ValueError:
            await self.bot.say("The tribe doesn't exist")

    @tfm.command(pass_context=True)
    async def avatar(self, ctx, *, user):
        """Get Transformice mouse avatar from Atelier801"""

        try:
            link = "http://api.micetigri.fr/json/player/{}".format(user)
            async with aiohttp.get(link) as m:
                result = await m.json()
                name = result['name']
                msg = "http://outil.derpolino.shost.ca/avatar/avatar.php?p={}".format(name)
                await self.bot.say(msg)
        except ValueError:
                await self.bot.say("Invalid username.")


def setup(bot):
    bot.add_cog(Transformice(bot))
