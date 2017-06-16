from typing import Tuple, MutableMapping, Any
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
            owner=None,
            coowners=[],
            whitelist=[],
            blacklist=[],
            enable_sentry=None
        )

        self.db.register_guild(
            prefix=[],
            whitelist=[],
            blacklist=[],
            admin_role=None,
            mod_role=None
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

        if "owner_id" not in kwargs:
            kwargs["owner_id"] = self.db.get("owner")

        self.counter = Counter()
        self.uptime = None
        self.delayed_load_info = {}
        super().__init__(**kwargs)

    async def is_owner(self, user):
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

    def delayed_load_extension(self, name: str, cog_dependencies: Tuple[str]=()):
        """
        This function allows you to delay loading of your cog until other cog
            dependencies have loaded.
        :param name: ALL LOWERCASE - the same name you use with the `load`
            command.
        :param cog_dependencies: ALL LOWERCASE - the same name you use
            with `load`. Should cog loading wait until these cogs have
            also loaded?
        :return:
        """

        if self.can_load_delayed(cog_dependencies):
            self.load_extension(name)
        else:
            self.delayed_load_info[name] = cog_dependencies

    def can_load_delayed(self, dependencies: Tuple[str]) -> bool:
        loaded_exts = [ext.split('.')[-1] for ext in self.extensions.keys()]

        for dep in dependencies:
            if not any(ext.endswith(dep) for ext in loaded_exts):
                return False
        return True

    def handle_load_extension(self, _: str):
        to_remove = []
        for name, deps in self.delayed_load_info.items():
            if self.can_load_delayed(deps):
                self.load_extension(name)
                to_remove.append(name)

        for name in to_remove:
            del self.delayed_load_info[name]

    def load_extension(self, name: str):
        try:
            super().load_extension(name)
        except:
            raise
        else:
            self.dispatch('load_extension', name)

    def unload_extension(self, name):
        try:
            super().unload_extension(name)
        except:
            raise
        else:
            self.dispatch('unload_extension', name)


class ExitCodes(Enum):
    CRITICAL = 1
    SHUTDOWN = 0
    RESTART  = 26