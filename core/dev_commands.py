from discord.ext import commands
from core.utils.chat_formatting import box
from core import checks
import asyncio
import discord


class Dev:
    """Various development focused utilities"""

    @commands.command()
    @checks.is_owner()
    async def debug(self, ctx, *, code):
        """Evaluates code"""
        author = ctx.author
        channel = ctx.channel

        code = code.strip('` ')
        result = None

        global_vars = globals().copy()
        global_vars['bot'] = ctx.bot
        global_vars['ctx'] = ctx
        global_vars['message'] = ctx.message
        global_vars['author'] = ctx.author
        global_vars['channel'] = ctx.channel
        global_vars['guild'] = ctx.guild

        try:
            result = eval(code, global_vars, locals())
        except Exception as e:
            await ctx.send('```py\n{}: {}```'.format(type(e).__name__, str(e)),)
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = str(result)

        if ctx.guild is not None:
            token = ctx.bot.http.token
            r = "[EXPUNGED]"
            result = result.replace(token, r)
            result = result.replace(token.lower(), r)
            result = result.replace(token.upper(), r)

        await ctx.send(box(result, lang="py"))

    @commands.command()
    @checks.is_owner()
    async def mock(self, ctx, user: discord.Member, *, command):
        """Runs a command as if it was issued by a different user

        The prefix must not be entered"""
        # Since we have stateful objects now this might be pretty bad
        # Sorry Danny
        old_author = ctx.author
        old_content = ctx.message.content
        ctx.message.author = user
        ctx.message.content = ctx.prefix + command

        await ctx.bot.process_commands(ctx.message)

        ctx.message.author = old_author
        ctx.message.content = old_content
