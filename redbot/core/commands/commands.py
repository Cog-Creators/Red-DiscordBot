"""Module for command helpers and classes.

This module contains extended classes and functions which are intended to
replace those from the `discord.ext.commands` module.
"""
import inspect
import weakref
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import discord
from discord.ext import commands

from . import converter as converters
from .errors import ConversionFailure
from .requires import PermState, PrivilegeLevel, Requires
from ..i18n import Translator

if TYPE_CHECKING:
    from .context import Context

__all__ = [
    "Cog",
    "CogCommandMixin",
    "CogGroupMixin",
    "Command",
    "Group",
    "GroupMixin",
    "command",
    "group",
]

_ = Translator("commands.commands", __file__)


class CogCommandMixin:
    """A mixin for cogs and commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self, Command):
            decorated = self.callback
        else:
            decorated = self
        self.requires: Requires = Requires(
            privilege_level=getattr(
                decorated, "__requires_privilege_level__", PrivilegeLevel.NONE
            ),
            user_perms=getattr(decorated, "__requires_user_perms__", {}),
            bot_perms=getattr(decorated, "__requires_bot_perms__", {}),
            checks=getattr(decorated, "__requires_checks__", []),
        )

    def allow_for(self, model_id: Union[int, str], guild_id: int) -> None:
        """Actively allow this command for the given model.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID to allow this cog or command in. For global
            rules, use ``0``.

        """
        self.requires.set_rule(model_id, PermState.ACTIVE_ALLOW, guild_id=guild_id)

    def deny_to(self, model_id: Union[int, str], guild_id: int) -> None:
        """Actively deny this command to the given model.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID to deny this cog or command in. For global
            rules, use ``0``.

        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        if cur_rule is PermState.PASSIVE_ALLOW:
            self.requires.set_rule(model_id, PermState.CAUTIOUS_ALLOW, guild_id=guild_id)
        else:
            self.requires.set_rule(model_id, PermState.ACTIVE_DENY, guild_id=guild_id)

    def clear_rule_for(
        self, model_id: Union[int, str], guild_id: int
    ) -> Tuple[PermState, PermState]:
        """Clear the rule which is currently set for this model.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID. For global rules, use ``0``.

        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        if cur_rule is PermState.ACTIVE_ALLOW:
            new_rule = PermState.NORMAL
        elif cur_rule is PermState.ACTIVE_DENY:
            new_rule = PermState.NORMAL
        elif cur_rule is PermState.CAUTIOUS_ALLOW:
            new_rule = PermState.PASSIVE_ALLOW
        else:
            return cur_rule, cur_rule
        self.requires.set_rule(model_id, new_rule, guild_id=guild_id)
        return cur_rule, new_rule

    def set_default_rule(self, rule: Optional[bool], guild_id: int) -> None:
        """Set the default rule for this cog or command.

        Parameters
        ----------
        rule : Optional[bool]
            The rule to set as default. If ``True`` for allow,
            ``False`` for deny and ``None`` for normal.
        guild_id : int
            The guild to set the default rule in. When ``0``, this will
            set the global default rule.

        """
        if rule is None:
            self.clear_rule_for(Requires.DEFAULT, guild_id=guild_id)
        elif rule is True:
            self.allow_for(Requires.DEFAULT, guild_id=guild_id)
        elif rule is False:
            self.deny_to(Requires.DEFAULT, guild_id=guild_id)


class Command(CogCommandMixin, commands.Command):
    """Command class for Red.

    This should not be created directly, and instead via the decorator.

    This class inherits from `discord.ext.commands.Command`. The
    attributes listed below are simply additions to the ones listed
    with that class.

    Attributes
    ----------
    checks : List[`coroutine function`]
        A list of check predicates which cannot be overridden, unlike
        `Requires.checks`.
    translator : Translator
        A translator for this command's help docstring.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._help_override = kwargs.pop("help_override", None)
        self.translator = kwargs.pop("i18n", None)

    @property
    def help(self):
        """Help string for this command.

        If the :code:`help` kwarg was passed into the decorator, it will
        default to that. If not, it will attempt to translate the docstring
        of the command's callback function.
        """
        if self._help_override is not None:
            return self._help_override
        if self.translator is None:
            translator = lambda s: s
        else:
            translator = self.translator
        command_doc = self.callback.__doc__
        if command_doc is None:
            return ""
        return inspect.cleandoc(translator(command_doc))

    @help.setter
    def help(self, value):
        # We don't want our help property to be overwritten, namely by super()
        pass

    @property
    def parents(self) -> List["Group"]:
        """List[commands.Group] : Returns all parent commands of this command.

        This is sorted by the length of :attr:`.qualified_name` from highest to lowest.
        If the command has no parents, this will be an empty list.
        """
        cmd = self.parent
        entries = []
        while cmd is not None:
            entries.append(cmd)
            cmd = cmd.parent
        return sorted(entries, key=lambda x: len(x.qualified_name), reverse=True)

    # noinspection PyMethodOverriding
    async def can_run(
        self,
        ctx: "Context",
        *,
        check_all_parents: bool = False,
        change_permission_state: bool = False,
    ) -> bool:
        """Check if this command can be run in the given context.

        This function first checks if the command can be run using
        discord.py's method `discord.ext.commands.Command.can_run`,
        then will return the result of `Requires.verify`.

        Keyword Arguments
        -----------------
        check_all_parents : bool
            If ``True``, this will check permissions for all of this
            command's parents and its cog as well as the command
            itself. Defaults to ``False``.
        change_permission_state : bool
            Whether or not the permission state should be changed as
            a result of this call. For most cases this should be
            ``False``. Defaults to ``False``.

        """
        ret = await super().can_run(ctx)
        if ret is False:
            return False

        # This is so contexts invoking other commands can be checked with
        # this command as well
        original_command = ctx.command
        original_state = ctx.permission_state
        ctx.command = self

        if check_all_parents is True:
            # Since we're starting from the beginning, we should reset the state to normal
            ctx.permission_state = PermState.NORMAL
            for parent in reversed(self.parents):
                try:
                    result = await parent.can_run(ctx, change_permission_state=True)
                except commands.CommandError:
                    result = False

                if result is False:
                    return False

        if self.parent is None and self.instance is not None:
            # For top-level commands, we need to check the cog's requires too
            ret = await self.instance.requires.verify(ctx)
            if ret is False:
                return False

        try:
            return await self.requires.verify(ctx)
        finally:
            ctx.command = original_command
            if not change_permission_state:
                ctx.permission_state = original_state

    async def _verify_checks(self, ctx):
        if not self.enabled:
            raise commands.DisabledCommand(f"{self.name} command is disabled")

        if not (await self.can_run(ctx, change_permission_state=True)):
            raise commands.CheckFailure(
                f"The check functions for command {self.qualified_name} failed."
            )

    async def do_conversion(
        self, ctx: "Context", converter, argument: str, param: inspect.Parameter
    ):
        """Convert an argument according to its type annotation.

        Raises
        ------
        ConversionFailure
            If doing the conversion failed.

        Returns
        -------
        Any
            The converted argument.

        """
        # Let's not worry about all of this junk if it's just a str converter
        if converter is str:
            return argument

        try:
            return await super().do_conversion(ctx, converter, argument, param)
        except commands.BadArgument as exc:
            raise ConversionFailure(converter, argument, param, *exc.args) from exc
        except ValueError as exc:
            # Some common converters need special treatment...
            if converter in (int, float):
                message = _('"{argument}" is not a number.').format(argument=argument)
                raise ConversionFailure(converter, argument, param, message) from exc

            # We should expose anything which might be a bug in the converter
            raise exc

    async def can_see(self, ctx: "Context"):
        """Check if this command is visible in the given context.

        In short, this will verify whether the user can run the
        command, and also whether the command is hidden or not.

        Parameters
        ----------
        ctx : `Context`
            The invocation context to check with.

        Returns
        -------
        bool
            ``True`` if this command is visible in the given context.

        """
        for cmd in (self, *self.parents):
            if cmd.hidden:
                return False
            try:
                can_run = await self.can_run(
                    ctx, check_all_parents=True, change_permission_state=False
                )
            except commands.CheckFailure:
                return False
            else:
                if can_run is False:
                    return False

        return True

    def disable_in(self, guild: discord.Guild) -> bool:
        """Disable this command in the given guild.

        Parameters
        ----------
        guild : discord.Guild
            The guild to disable the command in.

        Returns
        -------
        bool
            ``True`` if the command wasn't already disabled.

        """
        disabler = get_command_disabler(guild)
        if disabler in self.checks:
            return False
        else:
            self.checks.append(disabler)
            return True

    def enable_in(self, guild: discord.Guild) -> bool:
        """Enable this command in the given guild.

        Parameters
        ----------
        guild : discord.Guild
            The guild to enable the command in.

        Returns
        -------
        bool
            ``True`` if the command wasn't already enabled.

        """
        disabler = get_command_disabler(guild)
        try:
            self.checks.remove(disabler)
        except ValueError:
            return False
        else:
            return True

    def allow_for(self, model_id: Union[int, str], guild_id: int) -> None:
        super().allow_for(model_id, guild_id=guild_id)
        parents = self.parents
        if self.instance is not None:
            parents.append(self.instance)
        for parent in parents:
            cur_rule = parent.requires.get_rule(model_id, guild_id=guild_id)
            if cur_rule is PermState.NORMAL:
                parent.requires.set_rule(model_id, PermState.PASSIVE_ALLOW, guild_id=guild_id)
            elif cur_rule is PermState.ACTIVE_DENY:
                parent.requires.set_rule(model_id, PermState.CAUTIOUS_ALLOW, guild_id=guild_id)

    def clear_rule_for(
        self, model_id: Union[int, str], guild_id: int
    ) -> Tuple[PermState, PermState]:
        old_rule, new_rule = super().clear_rule_for(model_id, guild_id=guild_id)
        if old_rule is PermState.ACTIVE_ALLOW:
            parents = self.parents
            if self.instance is not None:
                parents.append(self.instance)
            for parent in parents:
                should_continue = parent.reevaluate_rules_for(model_id, guild_id=guild_id)[1]
                if not should_continue:
                    break
        return old_rule, new_rule

    def error(self, coro):
        """
        A decorator that registers a coroutine as a local error handler.

        A local error handler is an :func:`.on_command_error` event limited to
        a single command.

        The on_command_error event is still dispatched
        for commands with a dedicated error handler.

        Red's global error handler will ignore commands with a registered error handler.

        To have red handle specific errors with the default behavior,
        call ``Red.on_command_error`` with ``unhandled_by_cog`` set to True.

        For example:

            .. code-block:: python

                @a_command.error
                async def a_command_error_handler(self, ctx, error):

                    if isisntance(error, MyErrrorType):
                        self.log_exception(error)
                    else:
                        await ctx.bot.on_command_error(ctx, error, unhandled_by_cog=True)

        Parameters
        -----------
        coro : :term:`coroutine function`
            The coroutine to register as the local error handler.

        Raises
        -------
        discord.ClientException
            The coroutine is not actually a coroutine.
        """
        return super().error(coro)


class GroupMixin(discord.ext.commands.GroupMixin):
    """Mixin for `Group` and `Red` classes.

    This class inherits from :class:`discord.ext.commands.GroupMixin`.
    """

    def command(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.command` and adds it to
        the internal command list.
        """

        def decorator(func):
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator

    def group(self, *args, **kwargs):
        """A shortcut decorator that invokes :func:`.group` and adds it to
        the internal command list.
        """

        def decorator(func):
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result

        return decorator


class CogGroupMixin:
    requires: Requires
    all_commands: Dict[str, Command]

    def reevaluate_rules_for(
        self, model_id: Union[str, int], guild_id: Optional[int]
    ) -> Tuple[PermState, bool]:
        """Re-evaluate a rule by checking subcommand rules.

        This is called when a subcommand is no longer actively allowed.

        Parameters
        ----------
        model_id : Union[int, str]
            Must be an `int` if supplying an ID. `str` is only valid
            for "default".
        guild_id : int
            The guild ID. For global rules, use ``0``.

        Returns
        -------
        Tuple[PermState, bool]
            A 2-tuple containing the new rule and a bool indicating
            whether or not the rule was changed as a result of this
            call.

        """
        cur_rule = self.requires.get_rule(model_id, guild_id=guild_id)
        if cur_rule in (PermState.NORMAL, PermState.ACTIVE_ALLOW, PermState.ACTIVE_DENY):
            # These three states are unaffected by subcommand rules
            return cur_rule, False
        else:
            # Remaining states can be changed if there exists no actively-allowed
            # subcommand (this includes subcommands multiple levels below)
            if any(
                cmd.requires.get_rule(model_id, guild_id=guild_id) in PermState.ALLOWED_STATES
                for cmd in self.all_commands.values()
            ):
                return cur_rule, False
            elif cur_rule is PermState.PASSIVE_ALLOW:
                self.requires.set_rule(model_id, PermState.NORMAL, guild_id=guild_id)
                return PermState.NORMAL, True
            elif cur_rule is PermState.CAUTIOUS_ALLOW:
                self.requires.set_rule(model_id, PermState.ACTIVE_DENY, guild_id=guild_id)
                return PermState.ACTIVE_DENY, True


class Group(GroupMixin, Command, CogGroupMixin, commands.Group):
    """Group command class for Red.

    This class inherits from `Command`, with :class:`GroupMixin` and
    `discord.ext.commands.Group` mixed in.
    """

    def __init__(self, *args, **kwargs):
        self.autohelp = kwargs.pop("autohelp", True)
        super().__init__(*args, **kwargs)

    async def invoke(self, ctx: "Context"):
        view = ctx.view
        previous = view.index
        view.skip_ws()
        trigger = view.get_word()
        if trigger:
            ctx.subcommand_passed = trigger
            ctx.invoked_subcommand = self.all_commands.get(trigger, None)
        view.index = previous
        view.previous = previous

        if ctx.invoked_subcommand is None or self == ctx.invoked_subcommand:
            if self.autohelp and not self.invoke_without_command:
                await self._verify_checks(ctx)
                await ctx.send_help()
        elif self.invoke_without_command:
            # So invoke_without_command when a subcommand of this group is invoked
            # will skip the the invokation of *this* command. However, because of
            # how our permissions system works, we don't want it to skip the checks
            # as well.
            await self._verify_checks(ctx)

        await super().invoke(ctx)


class Cog(CogCommandMixin, CogGroupMixin):
    """Base class for a cog."""

    @property
    def all_commands(self) -> Dict[str, Command]:
        return {cmd.name: cmd for cmd in self.__class__.__dict__.values() if isinstance(cmd, Command)}


def command(name=None, cls=Command, **attrs):
    """A decorator which transforms an async function into a `Command`.

    Same interface as `discord.ext.commands.command`.
    """
    attrs["help_override"] = attrs.pop("help", None)
    return commands.command(name, cls, **attrs)


def group(name=None, **attrs):
    """A decorator which transforms an async function into a `Group`.

    Same interface as `discord.ext.commands.group`.
    """
    return command(name, cls=Group, **attrs)


__command_disablers = weakref.WeakValueDictionary()


def get_command_disabler(guild: discord.Guild) -> Callable[["Context"], Awaitable[bool]]:
    """Get the command disabler for a guild.

    A command disabler is a simple check predicate which returns
    ``False`` if the context is within the given guild.
    """
    try:
        return __command_disablers[guild]
    except KeyError:

        async def disabler(ctx: "Context") -> bool:
            if ctx.guild == guild:
                raise commands.DisabledCommand()
            return True

        __command_disablers[guild] = disabler
        return disabler
