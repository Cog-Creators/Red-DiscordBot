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
)

import discord

from .errors import BotMissingPermissions

if TYPE_CHECKING:
    from .context import Context

__all__ = ["DM_PERMS", "PrivilegeLevel", "Requires"]

_CoroFunc = Callable[..., Awaitable[Any]]
_CommandOrCoro = TypeVar("_CommandOrCoro", _CoroFunc, "Command")
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
        to execute the command. Note that for levels other than bot
        owner, the user can still run the command if they have the
        required `user_perms`.
    user_perms : discord.Permissions
        The required permissions for users to execute the command. Note
        that the user can still run the command if they have the
        required `privilege_level`.
    bot_perms : discord.Permissions
        The required bot permission for a command to be executed. This
        is not overrideable by other conditions.

    """

    def __init__(
        self,
        privilege_level: PrivilegeLevel,
        user_perms: Optional[Union[Dict[str, bool], discord.Permissions]],
        bot_perms: Optional[Union[Dict[str, bool], discord.Permissions]],
    ):
        self.checks: List[Callable[["Context"], Awaitable[bool]]] = []
        self.privilege_level: PrivilegeLevel = privilege_level

        if isinstance(user_perms, dict):
            self.user_perms: discord.Permissions = discord.Permissions.none()
            self.user_perms.update(**user_perms)
        else:
            self.user_perms = user_perms

        if isinstance(bot_perms, dict):
            self.bot_perms: discord.Permissions = discord.Permissions.none()
            self.bot_perms.update(**bot_perms)
        else:
            self.bot_perms = bot_perms

        self._global_rules: DefaultDict[_GlobalModel, bool] = _GlobalRuleDict(lambda: None)
        self._guild_rules: DefaultDict[discord.Guild, DefaultDict[_GuildModel, bool]] = (
            defaultdict(lambda: _GuildRuleDict(lambda: None))
        )

    @staticmethod
    def get_decorator(
        privilege_level: PrivilegeLevel, user_perms: Dict[str, bool]
    ) -> Callable[[_CoroFunc], bool]:
        def decorator(func: _CommandOrCoro) -> _CommandOrCoro:
            if asyncio.iscoroutinefunction(func):
                func.__requires_privilege_level__ = privilege_level
                func.__requires_user_perms__ = user_perms
            else:
                func.requires.privilege_level = privilege_level
                func.requires.user_perms.update(**user_perms)
            return func

        return decorator

    def add_global_rule(self, model: _GlobalModel, rule: bool) -> None:
        """Add a global rule for this command.

        This should be used to explicitly allow or deny the command to
        specific models globally. These rules take precedence over
        guild rules.

        Parameters
        ----------
        model : Union[discord.User, discord.Guild]
            The model to add a rule for.
        rule : bool
            ``True`` to allow, ``False`` to deny.

        """
        self._global_rules[self._member_as_user(model)] = rule

    def add_guild_rule(self, guild: discord.Guild, model: _GuildModel, rule: bool) -> None:
        """Add a guild-wide rule for this command.

        This should be used to explicitly allow or deny the command to
        specific models.

        Parameters
        ----------
        guild : discord.Guild
            The guild to add the rule in.
        model : Union[discord.Member, discord.Role, discord.abc.GuildChannel]
            The model to add a rule for.
        rule : bool
            ``True`` to allow, ``False`` to deny.

        """
        self._guild_rules[guild][model] = rule

    async def verify(self, ctx: "Context") -> bool:
        """Check if the given context passes the requirements.

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
        if ctx.guild is None:
            bot_user = ctx.bot.user
        else:
            bot_user = ctx.guild.me
        bot_perms = ctx.channel.permissions_for(bot_user)
        if not bot_perms >= self.bot_perms:
            raise BotMissingPermissions(missing=self._missing_perms(self.bot_perms, bot_perms))

        # Owner-only commands are non-overrideable
        if self.privilege_level == PrivilegeLevel.BOT_OWNER:
            return await ctx.bot.is_owner(ctx.author)

        rules_pass = self._verify_rules(ctx)
        if rules_pass is not None:
            return rules_pass

        checks_pass = await self._verify_checks(ctx)
        if checks_pass is False:
            return False

        user_perms = ctx.channel.permissions_for(ctx.author)
        if user_perms >= self.user_perms:
            return True

        privilege_level = await PrivilegeLevel.from_ctx(ctx)
        if privilege_level >= self.privilege_level:
            return True

        return False

    def _verify_rules(self, ctx: "Context") -> Optional[bool]:
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


class _GlobalRuleDict(defaultdict):
    def __missing__(self, key: Any) -> Any:
        if not isinstance(key, _GlobalModel.__args__):
            raise TypeError(f"Invalid type for global model: {type(key)}")
        return super().__missing__(key)


class _GuildRuleDict(defaultdict):
    def __missing__(self, key: Any) -> Any:
        if not isinstance(key, _GuildModel.__args__):
            raise TypeError(f"Invalid type for guild model: {type(key)}")
        return super().__missing__(key)
