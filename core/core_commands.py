from discord.ext import commands
from core import checks
import logging
import importlib
import os
import discord

log = logging.getLogger("red")


class Core:
    """Commands related to core functions"""

    @commands.command()
    @checks.is_owner()
    async def load(self, ctx, *, cog_name: str):
        """Loads a package"""
        if not cog_name.startswith("cogs."):
            cog_name = "cogs." + cog_name

        try:
            ctx.bot.load_extension(cog_name)
        except Exception as e:
            log.exception("Package loading failed", exc_info=e)
            await ctx.send("Failed to load package. Check your console or "
                           "logs for details.")
        else:
            await ctx.bot.save_packages_status()
            await ctx.send("Done.")

    @commands.group()
    @checks.is_owner()
    async def unload(self, ctx, *, cog_name: str):
        """Unloads a package"""
        if not cog_name.startswith("cogs."):
            cog_name = "cogs." + cog_name

        if cog_name in ctx.bot.extensions:
            ctx.bot.unload_extension(cog_name)
            await ctx.bot.save_packages_status()
            await ctx.send("Done.")
        else:
            await ctx.send("That extension is not loaded.")

    @commands.command(name="reload")
    @checks.is_owner()
    async def _reload(self, ctx, *, cog_name: str):
        """Reloads a package"""
        if not cog_name.startswith("cogs."):
            cog_name = "cogs." + cog_name

        try:
            self.refresh_modules(cog_name)
            ctx.bot.unload_extension(cog_name)
            ctx.bot.load_extension(cog_name)
        except Exception as e:
            log.exception("Package reloading failed", exc_info=e)
            await ctx.send("Failed to reload package. Check your console or "
                           "logs for details.")
        else:
            await ctx.bot.save_packages_status()
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
