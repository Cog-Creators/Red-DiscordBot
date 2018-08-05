import asyncio
import os
import logging
from collections import Counter
from enum import Enum
from importlib.machinery import ModuleSpec
from pathlib import Path

import discord
import sys
from discord.ext.commands.bot import BotBase
from discord.ext.commands import GroupMixin
from discord.ext.commands import when_mentioned_or

# This supresses the PyNaCl warning that isn't relevant here
from discord.voice_client import VoiceClient

VoiceClient.warn_nacl = False

from .cog_manager import CogManager
from . import Config, i18n, commands
from .rpc import RPCMixin
from .help_formatter import Help, help as help_
from .sentry import SentryManager


def _is_submodule(parent, child):
    return parent == child or child.startswith(parent + ".")


class RedBase(BotBase, RPCMixin):
    """Mixin for the main bot class.

    This exists because `Red` inherits from `discord.AutoShardedClient`, which
    is something other bot classes (namely selfbots) may not want to have as
    a parent class.

    Selfbots should inherit from this mixin along with `discord.Client`.
    """

    def __init__(self, *args, cli_flags=None, bot_dir: Path = Path.cwd(), **kwargs):
        self._shutdown_mode = ExitCodes.CRITICAL
        self.db = Config.get_core_conf(force_registration=True)
        self._co_owners = cli_flags.co_owner
        self.rpc_enabled = cli_flags.rpc
        self._last_exception = None
        self.db.register_global(
            token=None,
            prefix=[],
            packages=[],
            owner=None,
            whitelist=[],
            blacklist=[],
            enable_sentry=None,
            locale="en",
            embeds=True,
            color=15158332,
            fuzzy=False,
            help__page_char_limit=1000,
            help__max_pages_in_guild=2,
            help__tagline="",
        )

        self.db.register_guild(
            prefix=[],
            whitelist=[],
            blacklist=[],
            admin_role=None,
            mod_role=None,
            embeds=None,
            use_bot_color=False,
            fuzzy=False,
        )

        self.db.register_user(embeds=None)

        async def prefix_manager(bot, message):
            if not cli_flags.prefix:
                global_prefix = await bot.db.prefix()
            else:
                global_prefix = cli_flags.prefix
            if message.guild is None:
                return global_prefix
            server_prefix = await bot.db.guild(message.guild).prefix()
            if cli_flags.mentionable:
                return (
                    when_mentioned_or(*server_prefix)(bot, message)
                    if server_prefix
                    else when_mentioned_or(*global_prefix)(bot, message)
                )
            else:
                return server_prefix if server_prefix else global_prefix

        if "command_prefix" not in kwargs:
            kwargs["command_prefix"] = prefix_manager

        if cli_flags.owner and "owner_id" not in kwargs:
            kwargs["owner_id"] = cli_flags.owner

        if "owner_id" not in kwargs:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._dict_abuse(kwargs))

        if "command_not_found" not in kwargs:
            kwargs["command_not_found"] = "Command {} not found.\n{}"

        self.counter = Counter()
        self.uptime = None
        self.color = discord.Embed.Empty  # This is needed or color ends up 0x000000

        self.main_dir = bot_dir

        self.cog_mgr = CogManager(paths=(str(self.main_dir / "cogs"),))

        super().__init__(*args, formatter=Help(), **kwargs)

        self.remove_command("help")

        self.add_command(help_)

        self._sentry_mgr = None

    def enable_sentry(self):
        """Enable Sentry logging for Red."""
        if self._sentry_mgr is None:
            sentry_log = logging.getLogger("red.sentry")
            sentry_log.setLevel(logging.WARNING)
            self._sentry_mgr = SentryManager(sentry_log)
        self._sentry_mgr.enable()

    def disable_sentry(self):
        """Disable Sentry logging for Red."""
        if self._sentry_mgr is None:
            return
        self._sentry_mgr.disable()

    async def _dict_abuse(self, indict):
        """
        Please blame <@269933075037814786> for this.

        :param indict:
        :return:
        """

        indict["owner_id"] = await self.db.owner()
        i18n.set_locale(await self.db.locale())

    async def embed_requested(self, channel, user, command=None) -> bool:
        """
        Determine if an embed is requested for a response.

        Parameters
        ----------
        channel : `discord.abc.GuildChannel` or `discord.abc.PrivateChannel`
            The channel to check embed settings for.
        user : `discord.abc.User`
            The user to check embed settings for.
        command
            (Optional) the command ran.

        Returns
        -------
        bool
            :code:`True` if an embed is requested
        """
        if isinstance(channel, discord.abc.PrivateChannel) or (
            command and command == self.get_command("help")
        ):
            user_setting = await self.db.user(user).embeds()
            if user_setting is not None:
                return user_setting
        else:
            guild_setting = await self.db.guild(channel.guild).embeds()
            if guild_setting is not None:
                return guild_setting
        global_setting = await self.db.embeds()
        return global_setting

    async def is_owner(self, user):
        if user.id in self._co_owners:
            return True
        return await super().is_owner(user)

    async def is_admin(self, member: discord.Member):
        """Checks if a member is an admin of their guild."""
        admin_role = await self.db.guild(member.guild).admin_role()
        return any(role.id == admin_role for role in member.roles)

    async def is_mod(self, member: discord.Member):
        """Checks if a member is a mod or admin of their guild."""
        mod_role = await self.db.guild(member.guild).mod_role()
        admin_role = await self.db.guild(member.guild).admin_role()
        return any(role.id in (mod_role, admin_role) for role in member.roles)

    async def get_context(self, message, *, cls=commands.Context):
        return await super().get_context(message, cls=cls)

    def list_packages(self):
        """Lists packages present in the cogs the folder"""
        return os.listdir("cogs")

    async def save_packages_status(self, packages):
        await self.db.packages.set(packages)

    async def add_loaded_package(self, pkg_name: str):
        async with self.db.packages() as curr_pkgs:
            if pkg_name not in curr_pkgs:
                curr_pkgs.append(pkg_name)

    async def remove_loaded_package(self, pkg_name: str):
        async with self.db.packages() as curr_pkgs:
            while pkg_name in curr_pkgs:
                curr_pkgs.remove(pkg_name)

    async def load_extension(self, spec: ModuleSpec):
        name = spec.name.split(".")[-1]
        if name in self.extensions:
            raise discord.ClientException(f"there is already a package named {name} loaded")

        lib = spec.loader.load_module()
        if not hasattr(lib, "setup"):
            del lib
            raise discord.ClientException(f"extension {name} does not have a setup function")

        if asyncio.iscoroutinefunction(lib.setup):
            await lib.setup(self)
        else:
            lib.setup(self)

        self.extensions[name] = lib

    def remove_cog(self, cogname):
        super().remove_cog(cogname)

        for meth in self.rpc_handlers.pop(cogname.upper(), ()):
            self.unregister_rpc_handler(meth)

    def unload_extension(self, name):
        lib = self.extensions.get(name)

        if lib is None:
            return

        lib_name = lib.__name__  # Thank you

        # find all references to the module

        # remove the cogs registered from the module
        for cogname, cog in self.cogs.copy().items():
            if cog.__module__ and _is_submodule(lib_name, cog.__module__):
                self.remove_cog(cogname)

        # first remove all the commands from the module
        for cmd in self.all_commands.copy().values():
            if cmd.module and _is_submodule(lib_name, cmd.module):
                if isinstance(cmd, GroupMixin):
                    cmd.recursively_remove_all_commands()

                self.remove_command(cmd.name)

        # then remove all the listeners from the module
        for event_list in self.extra_events.copy().values():
            remove = []

            for index, event in enumerate(event_list):
                if event.__module__ and _is_submodule(lib_name, event.__module__):
                    remove.append(index)

            for index in reversed(remove):
                del event_list[index]

        try:
            func = getattr(lib, "teardown")
        except AttributeError:
            pass
        else:
            try:
                func(self)
            except:
                pass
        finally:
            # finally remove the import..
            pkg_name = lib.__package__
            del lib
            del self.extensions[name]

            for module in list(sys.modules):
                if _is_submodule(lib_name, module):
                    del sys.modules[module]

            if pkg_name.startswith("redbot.cogs."):
                del sys.modules["redbot.cogs"].__dict__[name]


class Red(RedBase, discord.AutoShardedClient):
    """
    You're welcome Caleb.
    """

    async def logout(self):
        """Logs out of Discord and closes all connections."""
        if self._sentry_mgr:
            await self._sentry_mgr.close()

        await super().logout()

    async def shutdown(self, *, restart: bool = False):
        """Gracefully quit Red.

        The program will exit with code :code:`0` by default.

        Parameters
        ----------
        restart : bool
            If :code:`True`, the program will exit with code :code:`26`. If the
            launcher sees this, it will attempt to restart the bot.

        """
        if not restart:
            self._shutdown_mode = ExitCodes.SHUTDOWN
        else:
            self._shutdown_mode = ExitCodes.RESTART

        await self.logout()


class ExitCodes(Enum):
    CRITICAL = 1
    SHUTDOWN = 0
    RESTART = 26
