from discord.ext import commands
from collections import Counter

from core import Config
from enum import Enum
import os


class Red(commands.Bot):
    def __init__(self, cli_flags, **kwargs):
        self._shutdown_mode = ExitCodes.CRITICAL
        self.db = Config.get_core_conf(force_registration=True)

        self.db.register_global(
            token=None,
            prefix=[],
            packages=[],
            coowners=[],
            admin_role=None,
            mod_role=None,
            whitelist=[],
            blacklist=[]
        )

        self.db.register_guild(
            prefix=[],
            whitelist=[],
            blacklist=[]
        )

        def prefix_manager(bot, message):
            if not cli_flags.prefix:
                global_prefix = self.db.prefix()
            else:
                global_prefix = cli_flags.prefix
            if message.guild is None:
                return global_prefix
            server_prefix = self.db.guild(message.guild).prefix()
            return server_prefix if server_prefix else global_prefix

        if "command_prefix" not in kwargs:
            kwargs["command_prefix"] = prefix_manager

        self.counter = Counter()
        self.uptime = None
        super().__init__(**kwargs)

    async def is_owner(self, user, allow_coowners=True):
        if allow_coowners:
            if user.id in self.db.coowners():
                return True
        return await super().is_owner(user)

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = await self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await ctx.send(page)
        else:
            pages = await self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await ctx.send(page)

    async def shutdown(self, *, restart=False):
        """Gracefully quits Red with exit code 0

        If restart is True, the exit code will be 26 instead
        Upon receiving that exit code, the launcher restarts Red"""
        if not restart:
            self._shutdown_mode = ExitCodes.SHUTDOWN
        else:
            self._shutdown_mode = ExitCodes.RESTART

        await self.logout()

    def list_packages(self):
        """Lists packages present in the cogs the folder"""
        return os.listdir("cogs")

    async def save_packages_status(self):
        loaded = []
        for package in self.extensions:
            if package.startswith("cogs."):
                loaded.append(package)
        await self.db.set("packages", loaded)


class ExitCodes(Enum):
    CRITICAL = 1
    SHUTDOWN = 0
    RESTART  = 26