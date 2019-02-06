"""
commands.requires
=================
This module manages the logic of resolving command permissions and
requirements. This includes rules which override those requirements,
as well as custom checks which can be overriden, and some special
checks like bot permissions checks.
"""
import asyncio
import enum
from typing import (
    Union,
    Optional,
    List,
    Callable,
    Awaitable,
    Dict,
    Any,
    TYPE_CHECKING,
    TypeVar,
    Tuple,
    ClassVar,
)

import discord

from .converter import GuildConverter
from .errors import BotMissingPermissions

if TYPE_CHECKING:
    from .commands import Command
    from .context import Context

    _CommandOrCoro = TypeVar("_CommandOrCoro", Callable[..., Awaitable[Any]], Command)

__all__ = [
    "CheckPredicate",
    "DM_PERMS",
    "GlobalPermissionModel",
    "GuildPermissionModel",
    "PermissionModel",
    "PrivilegeLevel",
    "PermState",
    "Requires",
    "permissions_check",
    "bot_has_permissions",
    "has_permissions",
    "is_owner",
    "guildowner",
    "guildowner_or_permissions",
    "admin",
    "admin_or_permissions",
    "mod",
    "mod_or_permissions",
]

_T = TypeVar("_T")
GlobalPermissionModel = Union[
    discord.User,
    discord.VoiceChannel,
    discord.TextChannel,
    discord.CategoryChannel,
    discord.Role,
    GuildConverter,  # Unfortunately this will have to do for now
]
GuildPermissionModel = Union[
    discord.Member,
    discord.VoiceChannel,
    discord.TextChannel,
    discord.CategoryChannel,
    discord.Role,
    GuildConverter,
]
PermissionModel = Union[GlobalPermissionModel, GuildPermissionModel]
CheckPredicate = Callable[["Context"], Union[Optional[bool], Awaitable[Optional[bool]]]]

# Here we are trying to model DM permissions as closely as possible. The only
# discrepancy I've found is that users can pin messages, but they cannot delete them.
# This means manage_messages is only half True, so it's left as False.
# This is also the same as the permissions returned when `permissions_for` is used in DM.
DM_PERMS = discord.Permissions.none()
DM_PERMS.update(
    add_reactions=True,
    attach_files=True,
    embed_links=True,
    external_emojis=True,
    mention_everyone=True,
    read_message_history=True,
    read_messages=True,
    send_messages=True,
)


class PrivilegeLevel(enum.IntEnum):
    """Enumeration for special privileges."""

    # Maintainer Note: do NOT re-order these.
    # Each privelege level also implies access to the ones before it.
    # Inserting new privelege levels at a later point is fine if that is considered.

    NONE = enum.auto()
    """No special privilege level."""

    MOD = enum.auto()
    """User has the mod role."""

    ADMIN = enum.auto()
    """User has the admin role."""

    GUILD_OWNER = enum.auto()
    """User is the guild level."""

    BOT_OWNER = enum.auto()
    """User is a bot owner."""

    @classmethod
    async def from_ctx(cls, ctx: "Context") -> "PrivilegeLevel":
        """Get a command author's PrivilegeLevel based on context."""
        if await ctx.bot.is_owner(ctx.author):
            return cls.BOT_OWNER
        elif ctx.guild is None:
            return cls.NONE
        elif ctx.author == ctx.guild.owner:
            return cls.GUILD_OWNER

        # The following is simply an optimised way to check if the user has the
        # admin or mod role.
        guild_settings = ctx.bot.db.guild(ctx.guild)
        admin_role_id = await guild_settings.admin_role()
        mod_role_id = await guild_settings.mod_role()
        is_mod = False
        for role in ctx.author.roles:
            if role.id == admin_role_id:
                return cls.ADMIN
            elif role.id == mod_role_id:
                is_mod = True
        if is_mod:
            return cls.MOD

        return cls.NONE

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}.{self.name}>"


class PermState(enum.Enum):
    """Enumeration for permission states used by rules."""

    ACTIVE_ALLOW = enum.auto()
    """This command has been actively allowed, default user checks
    should be ignored.
    """

    NORMAL = enum.auto()
    """No overrides have been set for this command, make determination
    from default user checks.
    """

    PASSIVE_ALLOW = enum.auto()
    """There exists a subcommand in the `ACTIVE_ALLOW` state, continue
    down the subcommand tree until we either find it or realise we're
    on the wrong branch.
    """

    CAUTIOUS_ALLOW = enum.auto()
    """This command has been actively denied, but there exists a
    subcommand in the `ACTIVE_ALLOW` state. This occurs when
    `PASSIVE_ALLOW` and `ACTIVE_DENY` are combined.
    """

    ACTIVE_DENY = enum.auto()
    """This command has been actively denied, terminate the command
    chain.
    """

    # The below are valid states, but should not be transitioned to
    # They should be set if they apply.

    ALLOWED_BY_HOOK = enum.auto()
    """This command has been actively allowed by a permission hook.
    check validation doesn't need this, but is useful to developers"""

    DENIED_BY_HOOK = enum.auto()
    """This command has been actively denied by a permission hook
    check validation doesn't need this, but is useful to developers"""

    def transition_to(
        self, next_state: "PermState"
    ) -> Tuple[Optional[bool], Union["PermState", Dict[bool, "PermState"]]]:
        return self.TRANSITIONS[self][next_state]

    @classmethod
    def from_bool(cls, value: Optional[bool]) -> "PermState":
        """Get a PermState from a bool or ``NoneType``."""
        if value is True:
            return cls.ACTIVE_ALLOW
        elif value is False:
            return cls.ACTIVE_DENY
        else:
            return cls.NORMAL

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}.{self.name}>"


# Here we're defining how we transition between states.
# The dict is in the form:
#   previous state -> this state -> Tuple[override, next state]
# "override" is a bool describing whether or not the command should be
# invoked. It can be None, in which case the default permission checks
# will be used instead.
# There is also one case where the "next state" is dependent on the
# result of the default permission checks - the transition from NORMAL
# to PASSIVE_ALLOW. In this case "next state" is a dict mapping the
# permission check results to the actual next state.
PermState.TRANSITIONS = {
    PermState.ACTIVE_ALLOW: {
        PermState.ACTIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),
        PermState.NORMAL: (True, PermState.ACTIVE_ALLOW),
        PermState.PASSIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),
        PermState.CAUTIOUS_ALLOW: (True, PermState.CAUTIOUS_ALLOW),
        PermState.ACTIVE_DENY: (False, PermState.ACTIVE_DENY),
    },
    PermState.NORMAL: {
        PermState.ACTIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),
        PermState.NORMAL: (None, PermState.NORMAL),
        PermState.PASSIVE_ALLOW: (True, {True: PermState.NORMAL, False: PermState.PASSIVE_ALLOW}),
        PermState.CAUTIOUS_ALLOW: (True, PermState.CAUTIOUS_ALLOW),
        PermState.ACTIVE_DENY: (False, PermState.ACTIVE_DENY),
    },
    PermState.PASSIVE_ALLOW: {
        PermState.ACTIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),
        PermState.NORMAL: (False, PermState.NORMAL),
        PermState.PASSIVE_ALLOW: (True, PermState.PASSIVE_ALLOW),
        PermState.CAUTIOUS_ALLOW: (True, PermState.CAUTIOUS_ALLOW),
        PermState.ACTIVE_DENY: (False, PermState.ACTIVE_DENY),
    },
    PermState.CAUTIOUS_ALLOW: {
        PermState.ACTIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),
        PermState.NORMAL: (False, PermState.ACTIVE_DENY),
        PermState.PASSIVE_ALLOW: (True, PermState.CAUTIOUS_ALLOW),
        PermState.CAUTIOUS_ALLOW: (True, PermState.CAUTIOUS_ALLOW),
        PermState.ACTIVE_DENY: (False, PermState.ACTIVE_DENY),
    },
    PermState.ACTIVE_DENY: {  # We can only start from ACTIVE_DENY if it is set on a cog.
        PermState.ACTIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),  # Should never happen
        PermState.NORMAL: (False, PermState.ACTIVE_DENY),
        PermState.PASSIVE_ALLOW: (False, PermState.ACTIVE_DENY),  # Should never happen
        PermState.CAUTIOUS_ALLOW: (False, PermState.ACTIVE_DENY),  # Should never happen
        PermState.ACTIVE_DENY: (False, PermState.ACTIVE_DENY),
    },
}
PermState.ALLOWED_STATES = (
    PermState.ACTIVE_ALLOW,
    PermState.PASSIVE_ALLOW,
    PermState.CAUTIOUS_ALLOW,
)


class Requires:
    """This class describes the requirements for executing a specific command.

    The permissions described include both bot permissions and user
    permissions.

    Attributes
    ----------
    checks : List[Callable[[Context], Union[bool, Awaitable[bool]]]]
        A list of checks which can be overridden by rules. Use
        `Command.checks` if you would like them to never be overridden.
    privilege_level : PrivilegeLevel
        The required privilege level (bot owner, admin, etc.) for users
        to execute the command. Can be ``None``, in which case the
        `user_perms` will be used exclusively, otherwise, for levels
        other than bot owner, the user can still run the command if
        they have the required `user_perms`.
    user_perms : Optional[discord.Permissions]
        The required permissions for users to execute the command. Can
        be ``None``, in which case the `privilege_level` will be used
        exclusively, otherwise, it will pass whether the user has the
        required `privilege_level` _or_ `user_perms`.
    bot_perms : discord.Permissions
        The required bot permissions for a command to be executed. This
        is not overrideable by other conditions.

    """

    DEFAULT: ClassVar[str] = "default"
    """The key for the default rule in a rules dict."""

    GLOBAL: ClassVar[int] = 0
    """Should be used in place of a guild ID when setting/getting
    global rules.
    """

    def __init__(
        self,
        privilege_level: Optional[PrivilegeLevel],
        user_perms: Union[Dict[str, bool], discord.Permissions, None],
        bot_perms: Union[Dict[str, bool], discord.Permissions],
        checks: List[CheckPredicate],
    ):
        self.checks: List[CheckPredicate] = checks
        self.privilege_level: Optional[PrivilegeLevel] = privilege_level

        if isinstance(user_perms, dict):
            self.user_perms: Optional[discord.Permissions] = discord.Permissions.none()
            _validate_perms_dict(user_perms)
            self.user_perms.update(**user_perms)
        else:
            self.user_perms = user_perms

        if isinstance(bot_perms, dict):
            self.bot_perms: discord.Permissions = discord.Permissions.none()
            _validate_perms_dict(bot_perms)
            self.bot_perms.update(**bot_perms)
        else:
            self.bot_perms = bot_perms
        self._global_rules: _RulesDict = _RulesDict()
        self._guild_rules: _IntKeyDict[_RulesDict] = _IntKeyDict[_RulesDict]()

    @staticmethod
    def get_decorator(
        privilege_level: Optional[PrivilegeLevel], user_perms: Dict[str, bool]
    ) -> Callable[["_CommandOrCoro"], "_CommandOrCoro"]:
        if not user_perms:
            user_perms = None

        def decorator(func: "_CommandOrCoro") -> "_CommandOrCoro":
            if asyncio.iscoroutinefunction(func):
                func.__requires_privilege_level__ = privilege_level
                func.__requires_user_perms__ = user_perms
            else:
                func.requires.privilege_level = privilege_level
                if user_perms is None:
                    func.requires.user_perms = None
                else:
                    _validate_perms_dict(user_perms)
                    func.requires.user_perms.update(**user_perms)
            return func

        return decorator

    def get_rule(self, model: Union[int, str, PermissionModel], guild_id: int) -> PermState:
        """Get the rule for a particular model.

        Parameters
        ----------
        model : Union[int, str, PermissionModel]
            The model to get the rule for. `str` is only valid for
            `Requires.DEFAULT`.
        guild_id : int
            The ID of the guild for the rule's scope. Set to
            `Requires.GLOBAL` for a global rule.

        Returns
        -------
        PermState
            The state for this rule. See the `PermState` class
            for an explanation.

        """
        if not isinstance(model, (str, int)):
            model = model.id
        if guild_id:
            rules = self._guild_rules.get(guild_id, _RulesDict())
        else:
            rules = self._global_rules
        return rules.get(model, PermState.NORMAL)

    def set_rule(self, model_id: Union[str, int], rule: PermState, guild_id: int) -> None:
        """Set the rule for a particular model.

        Parameters
        ----------
        model_id : Union[str, int]
            The model to add a rule for. `str` is only valid for
            `Requires.DEFAULT`.
        rule : PermState
            Which state this rule should be set as. See the `PermState`
            class for an explanation.
        guild_id : int
            The ID of the guild for the rule's scope. Set to
            `Requires.GLOBAL` for a global rule.

        """
        if guild_id:
            rules = self._guild_rules.setdefault(guild_id, _RulesDict())
        else:
            rules = self._global_rules
        if rule is PermState.NORMAL:
            rules.pop(model_id, None)
        else:
            rules[model_id] = rule

    def clear_all_rules(self, guild_id: int) -> None:
        """Clear all rules of a particular scope.

        This will preserve the default rule, if set.

        Parameters
        ----------
        guild_id : int
            The guild ID to clear rules for. If set to
            `Requires.GLOBAL`, this will clear all global rules and
            leave all guild rules untouched.

        """
        if guild_id:
            rules = self._guild_rules.setdefault(guild_id, _RulesDict())
        else:
            rules = self._global_rules
        default = rules.get(self.DEFAULT, None)
        rules.clear()
        if default is not None:
            rules[self.DEFAULT] = default

    async def verify(self, ctx: "Context") -> bool:
        """Check if the given context passes the requirements.

        This will check the bot permissions, overrides, user permissions
        and privilege level.

        Parameters
        ----------
        ctx : "Context"
            The invkokation context to check with.

        Returns
        -------
        bool
            ``True`` if the context passes the requirements.

        Raises
        ------
        BotMissingPermissions
            If the bot is missing required permissions to run the
            command.
        CommandError
            Propogated from any permissions checks.

        """
        await self._verify_bot(ctx)

        # Owner should never be locked out of commands for user permissions.
        if await ctx.bot.is_owner(ctx.author):
            return True
        # Owner-only commands are non-overrideable, and we already checked for owner.
        if self.privilege_level is PrivilegeLevel.BOT_OWNER:
            return False

        hook_result = await ctx.bot.verify_permissions_hooks(ctx)
        if hook_result is not None:
            return hook_result

        return await self._transition_state(ctx)

    async def _verify_bot(self, ctx: "Context") -> None:
        if ctx.guild is None:
            bot_user = ctx.bot.user
        else:
            bot_user = ctx.guild.me
        bot_perms = ctx.channel.permissions_for(bot_user)
        if not (bot_perms.administrator or bot_perms >= self.bot_perms):
            raise BotMissingPermissions(missing=self._missing_perms(self.bot_perms, bot_perms))

    async def _transition_state(self, ctx: "Context") -> bool:
        prev_state = ctx.permission_state
        cur_state = self._get_rule_from_ctx(ctx)
        should_invoke, next_state = prev_state.transition_to(cur_state)
        if should_invoke is None:
            # NORMAL invokation, we simply follow standard procedure
            should_invoke = await self._verify_user(ctx)
        elif isinstance(next_state, dict):
            # NORMAL to PASSIVE_ALLOW; should we proceed as normal or transition?
            # We must check what would happen normally, if no explicit rules were set.
            default_rule = PermState.NORMAL
            if ctx.guild is not None:
                default_rule = self.get_rule(self.DEFAULT, guild_id=ctx.guild.id)
            if default_rule is PermState.NORMAL:
                default_rule = self.get_rule(self.DEFAULT, self.GLOBAL)

            if default_rule == PermState.ACTIVE_DENY:
                would_invoke = False
            elif default_rule == PermState.ACTIVE_ALLOW:
                would_invoke = True
            else:
                would_invoke = await self._verify_user(ctx)
            next_state = next_state[would_invoke]

        ctx.permission_state = next_state
        return should_invoke

    async def _verify_user(self, ctx: "Context") -> bool:
        checks_pass = await self._verify_checks(ctx)
        if checks_pass is False:
            return False

        if self.user_perms is not None:
            user_perms = ctx.channel.permissions_for(ctx.author)
            if user_perms.administrator or user_perms >= self.user_perms:
                return True

        if self.privilege_level is not None:
            privilege_level = await PrivilegeLevel.from_ctx(ctx)
            if privilege_level >= self.privilege_level:
                return True

        return False

    def _get_rule_from_ctx(self, ctx: "Context") -> PermState:
        author = ctx.author
        guild = ctx.guild
        if ctx.guild is None:
            # We only check the user for DM channels
            rule = self._global_rules.get(author.id)
            if rule is not None:
                return rule
            return self.get_rule(self.DEFAULT, self.GLOBAL)

        rules_chain = [self._global_rules]
        guild_rules = self._guild_rules.get(ctx.guild.id)
        if guild_rules:
            rules_chain.append(guild_rules)

        channels = []
        if author.voice is not None:
            channels.append(author.voice.channel)
        channels.append(ctx.channel)
        category = ctx.channel.category
        if category is not None:
            channels.append(category)

        model_chain = [author, *channels, *author.roles, guild]

        for rules in rules_chain:
            for model in model_chain:
                rule = rules.get(model.id)
                if rule is not None:
                    return rule
            del model_chain[-1]  # We don't check for the guild in guild rules

        default_rule = self.get_rule(self.DEFAULT, guild.id)
        if default_rule is PermState.NORMAL:
            default_rule = self.get_rule(self.DEFAULT, self.GLOBAL)
        return default_rule

    async def _verify_checks(self, ctx: "Context") -> bool:
        if not self.checks:
            return True
        return await discord.utils.async_all(check(ctx) for check in self.checks)

    @staticmethod
    def _get_perms_for(ctx: "Context", user: discord.abc.User) -> discord.Permissions:
        if ctx.guild is None:
            return DM_PERMS
        else:
            return ctx.channel.permissions_for(user)

    @classmethod
    def _get_bot_perms(cls, ctx: "Context") -> discord.Permissions:
        return cls._get_perms_for(ctx, ctx.guild.me if ctx.guild else ctx.bot.user)

    @staticmethod
    def _missing_perms(
        required: discord.Permissions, actual: discord.Permissions
    ) -> discord.Permissions:
        # Explained in set theory terms:
        #   Assuming R is the set of required permissions, and A is
        #   the set of the user's permissions, the set of missing
        #   permissions will be equal to R \ A, i.e. the relative
        #   complement/difference of A with respect to R.
        relative_complement = required.value & ~actual.value
        return discord.Permissions(relative_complement)

    @staticmethod
    def _member_as_user(member: discord.abc.User) -> discord.User:
        if isinstance(member, discord.Member):
            # noinspection PyProtectedMember
            return member._user
        return member

    def __repr__(self) -> str:
        return (
            f"<Requires privilege_level={self.privilege_level!r} user_perms={self.user_perms!r} "
            f"bot_perms={self.bot_perms!r}>"
        )


# check decorators


def permissions_check(predicate: CheckPredicate):
    """An overwriteable version of `discord.ext.commands.check`.

    This has the same behaviour as `discord.ext.commands.check`,
    however this check can be ignored if the command is allowed
    through a permissions cog.
    """

    def decorator(func: "_CommandOrCoro") -> "_CommandOrCoro":
        if hasattr(func, "requires"):
            func.requires.checks.append(predicate)
        else:
            if not hasattr(func, "__requires_checks__"):
                func.__requires_checks__ = []
            # noinspection PyUnresolvedReferences
            func.__requires_checks__.append(predicate)
        return func

    return decorator


def bot_has_permissions(**perms: bool):
    """Complain if the bot is missing permissions.

    If the user tries to run the command, but the bot is missing the
    permissions, it will send a message describing which permissions
    are missing.

    This check cannot be overridden by rules.
    """

    def decorator(func: "_CommandOrCoro") -> "_CommandOrCoro":
        if asyncio.iscoroutinefunction(func):
            func.__requires_bot_perms__ = perms
        else:
            _validate_perms_dict(perms)
            func.requires.bot_perms.update(**perms)
        return func

    return decorator


def has_permissions(**perms: bool):
    """Restrict the command to users with these permissions.

    This check can be overridden by rules.
    """
    if perms is None:
        raise TypeError("Must provide at least one keyword argument to has_permissions")
    return Requires.get_decorator(None, perms)


def is_owner():
    """Restrict the command to bot owners.

    This check cannot be overridden by rules.
    """
    return Requires.get_decorator(PrivilegeLevel.BOT_OWNER, {})


def guildowner_or_permissions(**perms: bool):
    """Restrict the command to the guild owner or users with these permissions.

    This check can be overridden by rules.
    """
    return Requires.get_decorator(PrivilegeLevel.GUILD_OWNER, perms)


def guildowner():
    """Restrict the command to the guild owner.

    This check can be overridden by rules.
    """
    return guildowner_or_permissions()


def admin_or_permissions(**perms: bool):
    """Restrict the command to users with the admin role or these permissions.

    This check can be overridden by rules.
    """
    return Requires.get_decorator(PrivilegeLevel.ADMIN, perms)


def admin():
    """Restrict the command to users with the admin role.

    This check can be overridden by rules.
    """
    return admin_or_permissions()


def mod_or_permissions(**perms: bool):
    """Restrict the command to users with the mod role or these permissions.

    This check can be overridden by rules.
    """
    return Requires.get_decorator(PrivilegeLevel.MOD, perms)


def mod():
    """Restrict the command to users with the mod role.

    This check can be overridden by rules.
    """
    return mod_or_permissions()


class _IntKeyDict(Dict[int, _T]):
    """Dict subclass which throws KeyError when a non-int key is used."""

    def __getitem__(self, key: Any) -> _T:
        if not isinstance(key, int):
            raise TypeError("Keys must be of type `int`")
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: _T) -> None:
        if not isinstance(key, int):
            raise TypeError("Keys must be of type `int`")
        return super().__setitem__(key, value)


class _RulesDict(Dict[Union[int, str], PermState]):
    """Dict subclass which throws a KeyError when an invalid key is used."""

    def __getitem__(self, key: Any) -> PermState:
        if key != Requires.DEFAULT and not isinstance(key, int):
            raise TypeError(f'Expected "{Requires.DEFAULT}" or int key, not "{key}"')
        return super().__getitem__(key)

    def __setitem__(self, key: Any, value: PermState) -> None:
        if key != Requires.DEFAULT and not isinstance(key, int):
            raise TypeError(f'Expected "{Requires.DEFAULT}" or int key, not "{key}"')
        return super().__setitem__(key, value)


def _validate_perms_dict(perms: Dict[str, bool]) -> None:
    for perm, value in perms.items():
        try:
            attr = getattr(discord.Permissions, perm)
        except AttributeError:
            attr = None

        if attr is None or not isinstance(attr, property):
            # We reject invalid permissions
            raise TypeError(f"Unknown permission name '{perm}'")

        if value is not True:
            # We reject any permission not specified as 'True', since this is the only value which
            # makes practical sense.
            raise TypeError(f"Permission {perm} may only be specified as 'True', not {value}")
