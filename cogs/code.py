import discord

from discord.utils import find
from __main__ import send_cmd_help 
from discord.ext import commands
 
class Code:
    def __init__(self, bot):
        self.bot = bot
 
    @commands.group(pass_context=True, aliases=["language", "lng"])
    async def code(self, ctx):
        """Makes your text in a codeblock in a certain language"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return
    
    @code.command()
    async def python(self, *, content):
        msg = "```python\n"
        msg += content
        msg += "\n```"
        await self.bot.say(msg)

    @code.command()
    async def asciidoc(self, *, content):
        msg = "```asciidoc\n"
        msg += content
        msg += "\n```"
        await self.bot.say(msg)

    @code.command(aliases=['md'])
    async def markdown(self, *, content):
        msg = "```markdown\n"
        msg += content
        msg += "\n```"
        await self.bot.say(msg)
 
def setup(bot):
    bot.add_cog(Code(bot))