import asyncio
import inspect
import os
import logging
from collections import Counter
from enum import Enum
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Optional, Union, List

import discord
import sys
from discord.ext.commands import when_mentioned_or

from . import Config, i18n, commands, errors
from .cog_manager import CogManager
from .help_formatter import Help, help as help_
from .rpc import RPCMixin
from .sentry import SentryManager
from .utils import common_filters


def _is_submodule(parent, child):
    return parent == child or child.startswith(parent + ".")


class RedBase(commands.GroupMixin, commands.bot.BotBase, RPCMixin):
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
            disabled_commands=[],
            disabled_command_msg="That command is disabled.",
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
            disabled_commands=[],
            autoimmune_ids=[],
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
        self.checked_time_accuracy = None
        self.color = discord.Embed.Empty  # This is needed or color ends up 0x000000

        self.main_dir = bot_dir

        self.cog_mgr = CogManager(paths=(str(self.main_dir / "cogs"),))

        super().__init__(*args, formatter=Help(), **kwargs)

        self.remove_command("help")

        self.add_command(help_)

        self._sentry_mgr = None
        self._permissions_hooks: List[commands.CheckPredicate] = []

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

    async def process_commands(self, message: discord.Message):
        """
        modification from the base to do the same thing in the command case
        
        but dispatch an additional event for cogs which want to handle normal messages
        differently to command messages, 
        without the overhead of additional get_context calls per cog
        """
        if not message.author.bot:
            ctx = await self.get_context(message)
            if ctx.valid:
                return await self.invoke(ctx)

        self.dispatch("on_message_without_command", message)

    @staticmethod
    def list_packages():
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
            raise errors.PackageAlreadyLoaded(spec)

        lib = spec.loader.load_module()
        if not hasattr(lib, "setup"):
            del lib
            raise discord.ClientException(f"extension {name} does not have a setup function")

        if asyncio.iscoroutinefunction(lib.setup):
            await lib.setup(self)
        else:
            lib.setup(self)

        self.extensions[name] = lib

    def remove_cog(self, cogname: str):
        cog = self.get_cog(cogname)
        if cog is None:
            return

        for cls in inspect.getmro(cog.__class__):
            try:
                hook = getattr(cog, f"_{cls.__name__}__permissions_hook")
            except AttributeError:
                pass
            else:
                self.remove_permissions_hook(hook)

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
                if isinstance(cmd, discord.ext.commands.GroupMixin):
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

    async def is_automod_immune(
        self, to_check: Union[discord.Message, commands.Context, discord.abc.User, discord.Role]
    ) -> bool:
        """
        Checks if the user, message, context, or role should be considered immune from automated
        moderation actions.

        This will return ``False`` in direct messages.

        Parameters
        ----------
        to_check : `discord.Message` or `commands.Context` or `discord.abc.User` or `discord.Role`
            Something to check if it would be immune

        Returns
        -------
        bool
            ``True`` if immune

        """
        guild = to_check.guild
        if not guild:
            return False

        if isinstance(to_check, discord.Role):
            ids_to_check = [to_check.id]
        else:
            author = getattr(to_check, "author", to_check)
            ids_to_check = [r.id for r in author.roles]
            ids_to_check.append(author.id)

        immune_ids = await self.db.guild(guild).autoimmune_ids()

        return any(i in immune_ids for i in ids_to_check)

    @staticmethod
    async def send_filtered(
        destination: discord.abc.Messageable,
        filter_mass_mentions=True,
        filter_invite_links=True,
        filter_all_links=False,
        **kwargs,
    ):
        """
        This is a convienience wrapper around

        discord.abc.Messageable.send

        It takes the destination you'd like to send to, which filters to apply
        (defaults on mass mentions, and invite links) and any other parameters
        normally accepted by destination.send

        This should realistically only be used for responding using user provided
        input. (unfortunately, including usernames)
        Manually crafted messages which dont take any user input have no need of this
        """

        content = kwargs.pop("content", None)

        if content:
            if filter_mass_mentions:
                content = common_filters.filter_mass_mentions(content)
            if filter_invite_links:
                content = common_filters.filter_invites(content)
            if filter_all_links:
                content = common_filters.filter_urls(content)

        await destination.send(content=content, **kwargs)

    def add_cog(self, cog: commands.Cog):
        if not isinstance(cog, commands.Cog):
            raise RuntimeError(
                f"The {cog.__class__.__name__} cog in the {cog.__module__} package does "
                f"not inherit from the commands.Cog base class. The cog author must update "
                f"the cog to adhere to this requirement."
            )
        if not hasattr(cog, "requires"):
            commands.Cog.__init__(cog)

        for cls in inspect.getmro(cog.__class__):
            try:
                hook = getattr(cog, f"_{cls.__name__}__permissions_hook")
            except AttributeError:
                pass
            else:
                self.add_permissions_hook(hook)

        for attr in dir(cog):
            _attr = getattr(cog, attr)
            if isinstance(_attr, discord.ext.commands.Command) and not isinstance(
                _attr, commands.Command
            ):
                raise RuntimeError(
                    f"The {cog.__class__.__name__} cog in the {cog.__module__} package,"
                    " is not using Red's command module, and cannot be added. "
                    "If this is your cog, please use `from redbot.core import commands`"
                    "in place of `from discord.ext import commands`. For more details on "
                    "this requirement, see this page: "
                    "http://red-discordbot.readthedocs.io/en/v3-develop/framework_commands.html"
                )
        super().add_cog(cog)
        self.dispatch("cog_add", cog)

    def add_command(self, command: commands.Command):
        if not isinstance(command, commands.Command):
            raise TypeError("Command objects must derive from redbot.core.commands.Command")

        super().add_command(command)
        self.dispatch("command_add", command)

    def clear_permission_rules(self, guild_id: Optional[int]) -> None:
        """Clear all permission overrides in a scope.

        Parameters
        ----------
        guild_id : Optional[int]
            The guild ID to wipe permission overrides for. If
            ``None``, this will clear all global rules and leave all
            guild rules untouched.

        """
        for cog in self.cogs.values():
            cog.requires.clear_all_rules(guild_id)
        for command in self.walk_commands():
            command.requires.clear_all_rules(guild_id)

    def add_permissions_hook(self, hook: commands.CheckPredicate) -> None:
        """Add a permissions hook.

        Permissions hooks are check predicates which are called before
        calling `Requires.verify`, and they can optionally return an
        override: ``True`` to allow, ``False`` to deny, and ``None`` to
        default to normal behaviour.

        Parameters
        ----------
        hook
            A command check predicate which returns ``True``, ``False``
            or ``None``.

        """
        self._permissions_hooks.append(hook)

    def remove_permissions_hook(self, hook: commands.CheckPredicate) -> None:
        """Remove a permissions hook.

        Parameters are the same as those in `add_permissions_hook`.

        Raises
        ------
        ValueError
            If the permissions hook has not been added.

        """
        self._permissions_hooks.remove(hook)

    async def verify_permissions_hooks(self, ctx: commands.Context) -> Optional[bool]:
        """Run permissions hooks.

        Parameters
        ----------
        ctx : commands.Context
            The context for the command being invoked.

        Returns
        -------
        Optional[bool]
            ``False`` if any hooks returned ``False``, ``True`` if any
            hooks return ``True`` and none returned ``False``, ``None``
            otherwise.

        """
        hook_results = []
        for hook in self._permissions_hooks:
            result = await discord.utils.maybe_coroutine(hook, ctx)
            if result is not None:
                hook_results.append(result)
        if hook_results:
            return all(hook_results)


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
