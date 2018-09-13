import asyncio
import enum
from collections import defaultdict
from typing import (
    Union,
    Optional,
    List,
    Callable,
    Awaitable,
    DefaultDict,
    Dict,
    Any,
    TYPE_CHECKING,
    TypeVar,
    Tuple,
)

import discord

from .errors import BotMissingPermissions

if TYPE_CHECKING:
    from .commands import Command
    from .context import Context

    _CommandOrCoro = TypeVar("_CommandOrCoro", Callable[..., Awaitable[Any]], Command)

__all__ = [
    "DM_PERMS",
    "PrivilegeLevel",
    "PermissionState",
    "Requires",
    "has_permissions",
    "bot_has_permissions",
]

_GuildModel = Union[discord.Member, discord.Role, discord.abc.GuildChannel]
_GlobalModel = Union[discord.User, discord.Guild]

# Here we are trying to model DM permissions as closely as possible. The only
# discrepancy I've found is that users can pin messages, but they cannot delete them.
# This means manage_messages is only half True, so I've left it as False.
DM_PERMS = discord.Permissions.none()
DM_PERMS.update(
    add_reactions=True,
    read_messages=True,
    send_messages=True,
    embed_links=True,
    attach_files=True,
    read_message_history=True,
    external_emojis=True,
)


class PrivilegeLevel(enum.IntEnum):
    """Enumeration for special privileges."""

    NONE = enum.auto()
    MOD = enum.auto()
    ADMIN = enum.auto()
    GUILD_OWNER = enum.auto()
    BOT_OWNER = enum.auto()

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


class PermissionState(enum.Enum):
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

    def transition_to(
        self, next_state: "PermissionState"
    ) -> Tuple[Optional[bool], Union["PermissionState", Dict[bool, "PermissionState"]]]:
        return _TRANSITIONS[self][next_state]


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
_TRANSITIONS = {
    PermissionState.ACTIVE_ALLOW: {
        PermissionState.ACTIVE_ALLOW: (True, PermissionState.ACTIVE_ALLOW),
        PermissionState.NORMAL: (True, PermissionState.ACTIVE_ALLOW),
        PermissionState.PASSIVE_ALLOW: (True, PermissionState.ACTIVE_ALLOW),
        PermissionState.CAUTIOUS_ALLOW: (True, PermissionState.CAUTIOUS_ALLOW),
        PermissionState.ACTIVE_DENY: (False, PermissionState.ACTIVE_DENY),
    },
    PermissionState.NORMAL: {
        PermissionState.ACTIVE_ALLOW: (True, PermissionState.ACTIVE_ALLOW),
        PermissionState.NORMAL: (None, PermissionState.NORMAL),
        PermissionState.PASSIVE_ALLOW: (
            True,
            {True: PermissionState.NORMAL, False: PermissionState.PASSIVE_ALLOW},
        ),
        PermissionState.CAUTIOUS_ALLOW: (True, PermissionState.CAUTIOUS_ALLOW),
        PermissionState.ACTIVE_DENY: (False, PermissionState.ACTIVE_DENY),
    },
    PermissionState.PASSIVE_ALLOW: {
        PermissionState.ACTIVE_ALLOW: (True, PermissionState.ACTIVE_ALLOW),
        PermissionState.NORMAL: (False, PermissionState.NORMAL),
        PermissionState.PASSIVE_ALLOW: (True, PermissionState.PASSIVE_ALLOW),
        PermissionState.CAUTIOUS_ALLOW: (True, PermissionState.CAUTIOUS_ALLOW),
        PermissionState.ACTIVE_DENY: (False, PermissionState.ACTIVE_DENY),
    },
    PermissionState.CAUTIOUS_ALLOW: {
        PermissionState.ACTIVE_ALLOW: (True, PermissionState.ACTIVE_ALLOW),
        PermissionState.NORMAL: (False, PermissionState.ACTIVE_DENY),
        PermissionState.PASSIVE_ALLOW: (True, PermissionState.CAUTIOUS_ALLOW),
        PermissionState.CAUTIOUS_ALLOW: (True, PermissionState.CAUTIOUS_ALLOW),
        PermissionState.ACTIVE_DENY: (False, PermissionState.ACTIVE_DENY),
    },
}


class Requires:
    """This class describes the requirements for executing a specific command.

    The permissions described include both bot permissions and user
    permissions.

    Attributes
    ----------
    checks : List[`coroutine function`]
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

    def __init__(
        self,
        privilege_level: Optional[PrivilegeLevel],
        user_perms: Union[Dict[str, bool], discord.Permissions, None],
        bot_perms: Union[Dict[str, bool], discord.Permissions],
    ):
        self.checks: List[Callable[["Context"], Awaitable[bool]]] = []
        self.privilege_level: Optional[PrivilegeLevel] = privilege_level

        if isinstance(user_perms, dict):
            self.user_perms: Optional[discord.Permissions] = discord.Permissions.none()
            self.user_perms.update(**user_perms)
        else:
            self.user_perms = user_perms

        if isinstance(bot_perms, dict):
            self.bot_perms: discord.Permissions = discord.Permissions.none()
            self.bot_perms.update(**bot_perms)
        else:
            self.bot_perms = bot_perms

        self._global_rules: _GlobalRuleDict = _GlobalRuleDict(lambda: None)
        self._guild_rules: DefaultDict[discord.Guild, _GuildRuleDict] = defaultdict(
            lambda: _GuildRuleDict(lambda: None)
        )

    @staticmethod
    def get_decorator(
        privilege_level: Optional[PrivilegeLevel], user_perms: Dict[str, bool]
    ) -> Callable[["_CommandOrCoro"], bool]:
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
                    func.requires.user_perms.update(**user_perms)
            return func

        return decorator

    def add_global_rule(self, model: _GlobalModel, rule: PermissionState) -> None:
        """Add a global rule for this command.

        This should be used to explicitly allow or deny the command to
        specific models globally. These rules take precedence over
        guild rules.

        Parameters
        ----------
        model : Union[discord.User, discord.Guild]
            The model to add a rule for.
        rule : PermissionState
            Which state this rule should be set as. See the `PermissionState`
            class for an explanation.

        """
        self._global_rules[self._member_as_user(model)] = rule

    def add_guild_rule(
        self, guild: discord.Guild, model: _GuildModel, rule: PermissionState
    ) -> None:
        """Add a guild-wide rule for this command.

        This should be used to explicitly allow or deny the command to
        specific models.

        Parameters
        ----------
        guild : discord.Guild
            The guild to add the rule in.
        model : Union[discord.Member, discord.Role, discord.abc.GuildChannel]
            The model to add a rule for.
        rule : PermissionState
            Which state this rule should be set as. See the `PermissionState`
            class for an explanation.

        """
        self._guild_rules[guild][model] = rule

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

        """
        await self._verify_bot(ctx)

        # Owner-only commands are non-overrideable
        if self.privilege_level is PrivilegeLevel.BOT_OWNER:
            return await ctx.bot.is_owner(ctx.author)

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
        cur_state = self._get_rule(ctx)
        should_invoke, next_state = prev_state.transition_to(cur_state)
        if should_invoke is None:
            # NORMAL invokation, we simply follow standard procedure
            should_invoke = await self._verify_user(ctx)
        elif isinstance(next_state, dict):
            # NORMAL to PASSIVE_ALLOW; should we proceed as normal or transition?
            next_state = next_state[await self._verify_user(ctx)]

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

    def _get_rule(self, ctx: "Context") -> PermissionState:
        # Check global rules first
        rule = self._global_rules[self._member_as_user(ctx.author)]
        if rule is not None:
            return rule

        if ctx.guild is not None:
            rule = self._global_rules[ctx.guild]
            if rule is not None:
                return rule

            # Check guild rules next
            rules = self._guild_rules[ctx.guild]
            for model in (ctx.author, *ctx.author.roles, ctx.channel, ctx.channel.category):
                rule = rules[model]
                if rule is not None:
                    return rule

        return PermissionState.NORMAL

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


# check decorators


def has_permissions(**perms) -> Callable[["_CommandOrCoro"], "_CommandOrCoro"]:
    """Command decorator for verifying the author has required permissions."""
    return Requires.get_decorator(None, perms)


def bot_has_permissions(**perms) -> Callable[["_CommandOrCoro"], "_CommandOrCoro"]:
    """Command decorator for verifying the bot has required permissions."""

    def decorator(func: "_CommandOrCoro") -> "_CommandOrCoro":
        if asyncio.iscoroutinefunction(func):
            func.__requires_bot_perms__ = perms
        else:
            func.requires.bot_perms.update(**perms)
        return func

    return decorator


class _GlobalRuleDict(DefaultDict[_GlobalModel, Optional[PermissionState]]):
    def __missing__(self, key: Any) -> Any:
        if not isinstance(key, _GlobalModel.__args__):
            raise TypeError(f"Invalid type for global model: {type(key)}")
        return super().__missing__(key)


class _GuildRuleDict(DefaultDict[_GuildModel, Optional[PermissionState]]):
    def __missing__(self, key: Any) -> Any:
        if not isinstance(key, _GuildModel.__args__):
            raise TypeError(f"Invalid type for guild model: {type(key)}")
        return super().__missing__(key)
