import asyncio
from importlib.machinery import ModuleSpec

import discord
from discord.ext import commands
from collections import Counter

from discord.ext.commands import GroupMixin
from pathlib import Path

from core import Config
from enum import Enum
import os

from core.cog_manager import CogManager
from core import i18n


class Red(commands.Bot):
    def __init__(self, cli_flags, bot_dir: Path=Path.cwd(), **kwargs):
        self._shutdown_mode = ExitCodes.CRITICAL
        self.db = Config.get_core_conf(force_registration=True)
        self._co_owners = cli_flags.co_owner

        self.db.register_global(
            token=None,
            prefix=[],
            packages=[],
            owner=None,
            whitelist=[],
            blacklist=[],
            enable_sentry=None,
            locale='en'
        )

        self.db.register_guild(
            prefix=[],
            whitelist=[],
            blacklist=[],
            admin_role=None,
            mod_role=None
        )

        async def prefix_manager(bot, message):
            if not cli_flags.prefix:
                global_prefix = await bot.db.prefix()
            else:
                global_prefix = cli_flags.prefix
            if message.guild is None:
                return global_prefix
            server_prefix = await bot.db.guild(message.guild).prefix()
            return server_prefix if server_prefix else global_prefix

        if "command_prefix" not in kwargs:
            kwargs["command_prefix"] = prefix_manager

        if cli_flags.owner and "owner_id" not in kwargs:
            kwargs["owner_id"] = cli_flags.owner

        if "owner_id" not in kwargs:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._dict_abuse(kwargs))

        self.counter = Counter()
        self.uptime = None

        self.main_dir = bot_dir

        self.cog_mgr = CogManager(paths=(str(self.main_dir / 'cogs'),),
                                  bot_dir=self.main_dir)

        super().__init__(**kwargs)

    async def _dict_abuse(self, indict):
        """
        Please blame <@269933075037814786> for this.

        :param indict:
        :return:
        """

        indict['owner_id'] = await self.db.owner()
        i18n.set_locale(await self.db.locale())

    async def is_owner(self, user):
        if user.id in self._co_owners:
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

    async def save_packages_status(self, packages):
        await self.db.packages.set(packages)

    async def add_loaded_package(self, pkg_name: str):
        curr_pkgs = await self.db.packages()
        if pkg_name not in curr_pkgs:
            curr_pkgs.append(pkg_name)
            await self.save_packages_status(curr_pkgs)

    async def remove_loaded_package(self, pkg_name: str):
        curr_pkgs = await self.db.packages()
        if pkg_name in curr_pkgs:
            await self.save_packages_status([p for p in curr_pkgs if p != pkg_name])

    def load_extension(self, spec: ModuleSpec):
        name = spec.name.split('.')[-1]
        if name in self.extensions:
            return

        lib = spec.loader.load_module()
        if not hasattr(lib, 'setup'):
            del lib
            raise discord.ClientException('extension does not have a setup function')

        lib.setup(self)
        self.extensions[name] = lib

    def unload_extension(self, name):
        lib = self.extensions.get(name)
        if lib is None:
            return

        lib_name = lib.__name__  # Thank you

        # find all references to the module

        # remove the cogs registered from the module
        for cogname, cog in self.cogs.copy().items():
            if cog.__module__.startswith(lib_name):
                self.remove_cog(cogname)

        # first remove all the commands from the module
        for cmd in self.all_commands.copy().values():
            if cmd.module.startswith(lib_name):
                if isinstance(cmd, GroupMixin):
                    cmd.recursively_remove_all_commands()
                self.remove_command(cmd.name)

        # then remove all the listeners from the module
        for event_list in self.extra_events.copy().values():
            remove = []
            for index, event in enumerate(event_list):
                if event.__module__.startswith(lib_name):
                    remove.append(index)

            for index in reversed(remove):
                del event_list[index]

        try:
            func = getattr(lib, 'teardown')
        except AttributeError:
            pass
        else:
            try:
                func(self)
            except:
                pass
        finally:
            # finally remove the import..
            del lib
            del self.extensions[name]
            # del sys.modules[name]


class ExitCodes(Enum):
    CRITICAL = 1
    SHUTDOWN = 0
    RESTART  = 26