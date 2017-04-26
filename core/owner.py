from discord.ext import commands
from core import checks
from core.utils.chat_formatting import box
import asyncio
import importlib
import os
import discord


class Owner:
    """All owner-only commands that relate to debug bot operations."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.is_owner()
    async def load(self, ctx, *, cog_name: str):
        """Loads a package"""
        if not cog_name.startswith("cogs."):
            cog_name = "cogs." + cog_name
        self.bot.load_extension(cog_name)
        await ctx.send("Done.")

    @commands.group()
    @checks.is_owner()
    async def unload(self, ctx, *, cog_name: str):
        """Unloads a package"""
        if not cog_name.startswith("cogs."):
            cog_name = "cogs." + cog_name
        if cog_name in self.bot.extensions:
            self.bot.unload_extension(cog_name)
            await ctx.send("Done.")
        else:
            await ctx.send("That extension is not loaded.")

    @commands.command(name="reload")
    @checks.is_owner()
    async def _reload(self, ctx, *, cog_name: str):
        """Reloads a package"""
        if not cog_name.startswith("cogs."):
            cog_name = "cogs." + cog_name
        self.refresh_modules(cog_name)
        self.bot.unload_extension(cog_name)
        self.bot.load_extension(cog_name)
        await ctx.send("Done.")

    def refresh_modules(self, module):
        """Interally reloads modules so that changes are detected"""
        module = module.replace(".", os.sep)
        for root, dirs, files in os.walk(module):
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    path, _ = os.path.splitext(path)
                    path = ".".join(path.split(os.sep))
                    print("Reloading " + path)
                    m = importlib.import_module(path)
                    importlib.reload(m)

    @commands.command(hidden=True)
    @checks.is_owner()
    async def debug(self, ctx, *, code):
        """Evaluates code"""
        author = ctx.message.author
        channel = ctx.message.channel

        code = code.strip('` ')
        result = None

        global_vars = globals().copy()
        global_vars['bot'] = self.bot
        global_vars['ctx'] = ctx
        global_vars['message'] = ctx.message
        global_vars['author'] = ctx.message.author
        global_vars['channel'] = ctx.message.channel
        global_vars['guild'] = ctx.message.guild

        try:
            result = eval(code, global_vars, locals())
        except Exception as e:
            await ctx.send('```py\n{}: {}```'.format(type(e).__name__, str(e)),)
            return

        if asyncio.iscoroutine(result):
            result = await result

        result = str(result)

        if ctx.message.guild is not None:
            token = ctx.bot.http.token
            r = "[EXPUNGED]"
            result = result.replace(token, r)
            result = result.replace(token.lower(), r)
            result = result.replace(token.upper(), r)

        await ctx.send(box(result, lang="py"))

    @commands.command(hidden=True)
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

        await self.bot.process_commands(ctx.message)

        ctx.message.author = old_author
        ctx.message.content = old_content
