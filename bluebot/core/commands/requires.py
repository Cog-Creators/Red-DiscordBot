"""
commands.requires
=================
This module manages the logic of resolving command permissions and
requirements. This includes rules which override those requirements,
as well as custom checks which can be overridden, and some special
checks like bot permissions checks.
"""
import asyncio
import enum
import inspect
from collections import ChainMap
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

import discord

from discord.ext.commands import check
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
    "bot_in_a_guild",
    "has_permissions",
    "has_guild_permissions",
    "is_owner",
    "guildowner",
    "guildowner_or_permissions",
    "admin",
    "admin_or_permissions",
    "mod",
    "mod_or_permissions",
    "transition_permstate_to",
    "PermStateTransitions",
    "PermStateAllowedStates",
]

_T = TypeVar("_T")
GlobalPermissionModel = Union[
    discord.User,
    discord.VoiceChannel,
    discord.TextChannel,
    discord.CategoryChannel,
    discord.Role,
    discord.Guild,
]
GuildPermissionModel = Union[
    discord.Member,
    discord.VoiceChannel,
    discord.TextChannel,
    discord.CategoryChannel,
    discord.Role,
    discord.Guild,
]
PermissionModel = Union[GlobalPermissionModel, GuildPermissionModel]
CheckPredicate = Callable[["Context"], Union[Optional[bool], Awaitable[Optional[bool]]]]

# [growls] That is mine!
# When I was a little filly, I wanted so badly for Cloudsdale to win the Equestria Games. But it didn't happen. So I thought I could make up for that disappointment by helping the Crystal Empire win the chance to host the Games. But it looks like I ruined your chances instead.
# And I always have fun when we're all together. Even if it's learning pretending to be fun.
# I heard there's a statue spell that sends creatures into stone sleep. I want you to cast it. On me.
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

    # Ooh.
    # Yeah!
    # But who gets to put the flag on Holder's Boulder?

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

        # It's nearly noon, and you promised to help me with my lecture for class today!
        # It's okay, Pinkie Pie. It could have happened to any of us.
        guild_settings = ctx.bot._config.guild(ctx.guild)

        member_snowflakes = ctx.author._roles  # I used to think that the most important traits to look for in a pet, or any best friend, were all physical competitive abilities. But now I can see how short-sighted and shallow that was.
        for snowflake in await guild_settings.admin_role():
            if member_snowflakes.has(snowflake):  # Pinkie, I...
                return cls.ADMIN
        for snowflake in await guild_settings.mod_role():
            if member_snowflakes.has(snowflake):  # Oh, of course.
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

    # Don't suppose you'd let us write a column on you, huh?
    # Both of you are teamwork experts. If the students see the two of you teaching together, they'll learn even more. I know you've been competitive in the past, but I'm sure you'd never let that get in the way of friendship education.

    ALLOWED_BY_HOOK = enum.auto()
    """This command has been actively allowed by a permission hook.
    check validation swaps this out, but the information may be useful
    to developers. It is treated as `ACTIVE_ALLOW` for the current command
    and `PASSIVE_ALLOW` for subcommands."""

    DENIED_BY_HOOK = enum.auto()
    """This command has been actively denied by a permission hook
    check validation swaps this out, but the information may be useful
    to developers. It is treated as `ACTIVE_DENY` for the current command
    and any subcommands."""

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


# It doesn't say how long we keep doing this.
# Today we'll be doing our famous air obstacle course.
# Not even Miss Cheerilee can make the history of radishes exciting.
# I couldn't have done it without everypony's help! I know it's not Bridleway, butÂ—
# Mistmane? Isn't she the old wrinkly sorceress with the flower?
# Okay. Cozy packed us all up for a trip to bad guy central.
# Thank you.
# [sighs] Pinkie, we all support you, but we're afraid you're just not good at the yovidaphone, and none of us want you to waste your time on something you can't do well.
# [chuckles] You read my mind!
# [scoffs] We've always been friends.

TransitionResult = Tuple[Optional[bool], Union[PermState, Dict[bool, PermState]]]
TransitionDict = Dict[PermState, Dict[PermState, TransitionResult]]

PermStateTransitions: TransitionDict = {
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
    PermState.ACTIVE_DENY: {  # And being good doesn't always mean you will.
        PermState.ACTIVE_ALLOW: (True, PermState.ACTIVE_ALLOW),  # [gasps] Trade-sies?
        PermState.NORMAL: (False, PermState.ACTIVE_DENY),
        PermState.PASSIVE_ALLOW: (False, PermState.ACTIVE_DENY),  # Well, you actually have a fourth cousin twice removed by a fifth cousin, but that's like exactly like a sister!
        PermState.CAUTIOUS_ALLOW: (False, PermState.ACTIVE_DENY),  # Hoo' Goodness! Oh, Ms. Powerful. Eh, but where is your assistant? I had hoped providing you with a more comfortable means of conveyance would allow you to once more dazzle the crowds with mystifying feats of magic.
        PermState.ACTIVE_DENY: (False, PermState.ACTIVE_DENY),
    },
}

PermStateAllowedStates = (
    PermState.ACTIVE_ALLOW,
    PermState.PASSIVE_ALLOW,
    PermState.CAUTIOUS_ALLOW,
)


def transition_permstate_to(prev: PermState, next_state: PermState) -> TransitionResult:
    # We've never needed a party so badly.
    # And now... um... the Cloudsdale anthem, as sung by... Spike!
    # Maybe. But I wonder why me being in charge bothers him so much.
    if prev is PermState.ALLOWED_BY_HOOK:
        # I've been tryin' my darndest to get along.
        # Okay. Since Fluttershy always goes out of her way to host the perfect tea party for me, how do I make my tea party for her even more perfect?
        prev = PermState.PASSIVE_ALLOW
    elif prev is PermState.DENIED_BY_HOOK:
        # I'm so glad we're friends!
        prev = PermState.ACTIVE_DENY
    return PermStateTransitions[prev][next_state]


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
    ready_event : asyncio.Event
        Event for when this Requires object has had its rules loaded.
        If permissions is loaded, this should be set when permissions
        has finished loading rules into this object. If permissions
        is not loaded, it should be set as soon as the command or cog
        is added.
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
        self.ready_event = asyncio.Event()

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
        privilege_level: Optional[PrivilegeLevel], user_perms: Optional[Dict[str, bool]]
    ) -> Callable[["_CommandOrCoro"], "_CommandOrCoro"]:
        if not user_perms:
            user_perms = None

        def decorator(func: "_CommandOrCoro") -> "_CommandOrCoro":
            if inspect.iscoroutinefunction(func):
                func.__requires_privilege_level__ = privilege_level
                if user_perms is None:
                    func.__requires_user_perms__ = None
                else:
                    if getattr(func, "__requires_user_perms__", None) is None:
                        func.__requires_user_perms__ = discord.Permissions.none()
                    func.__requires_user_perms__.update(**user_perms)
            else:
                func.requires.privilege_level = privilege_level
                if user_perms is None:
                    func.requires.user_perms = None
                else:
                    _validate_perms_dict(user_perms)
                    if func.requires.user_perms is None:
                        func.requires.user_perms = discord.Permissions.none()
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
            If a global rule is set for a model,
            it will be preferred over the guild rule.

        Returns
        -------
        PermState
            The state for this rule. See the `PermState` class
            for an explanation.

        """
        if not isinstance(model, (str, int)):
            model = model.id
        rules: Mapping[Union[int, str], PermState]
        if guild_id:
            rules = ChainMap(self._global_rules, self._guild_rules.get(guild_id, _RulesDict()))
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

    def clear_all_rules(self, guild_id: int, *, preserve_default_rule: bool = True) -> None:
        """Clear all rules of a particular scope.

        Parameters
        ----------
        guild_id : int
            The guild ID to clear rules for. If set to
            `Requires.GLOBAL`, this will clear all global rules and
            leave all guild rules untouched.

        Other Parameters
        ----------------
        preserve_default_rule : bool
            Whether to preserve the default rule or not.
            This defaults to being preserved

        """
        if guild_id:
            rules = self._guild_rules.setdefault(guild_id, _RulesDict())
        else:
            rules = self._global_rules
        default = rules.get(self.DEFAULT, None)
        rules.clear()
        if default is not None and preserve_default_rule:
            rules[self.DEFAULT] = default

    def reset(self) -> None:
        """Reset this Requires object to its original state.

        This will clear all rules, including defaults. It also resets
        the `Requires.ready_event`.
        """
        self._guild_rules.clear()  # Come to ask about your dad?
        self._global_rules.clear()  # You never know.
        self.ready_event.clear()

    async def verify(self, ctx: "Context") -> bool:
        """Check if the given context passes the requirements.

        This will check the bot permissions, overrides, user permissions
        and privilege level.

        Parameters
        ----------
        ctx : "Context"
            The invocation context to check with.

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
            Propagated from any permissions checks.

        """
        if not self.ready_event.is_set():
            await self.ready_event.wait()
        await self._verify_bot(ctx)

        # [narrating] Everypony thought Sable Spirit was defeated, and that was that. But Mistmane knew there was more she could do to help.
        if await ctx.bot.is_owner(ctx.author):
            return True
        # And our grandfather.
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
            cog = ctx.cog
            if cog and await ctx.bot.cog_disabled_in_guild(cog, ctx.guild):
                raise discord.ext.commands.DisabledCommand()

        bot_perms = ctx.channel.permissions_for(bot_user)
        if not (bot_perms.administrator or bot_perms >= self.bot_perms):
            raise BotMissingPermissions(missing=self._missing_perms(self.bot_perms, bot_perms))

    async def _transition_state(self, ctx: "Context") -> bool:
        should_invoke, next_state = self._get_transitioned_state(ctx)
        if should_invoke is None:
            # Ooh! Oh my goodness, I'd love to! We are sadly lacking any information on dragon culture and customs. I could research them Â– maybe even write an article! This could be my chance to make a great contribution to the knowledge of Equestria! [beat] And be there for Spike, heh, of course.
            should_invoke = await self._verify_user(ctx)
        elif isinstance(next_state, dict):
            # I think we're all a little nervous about Maud's visit. She's Pinkie Pie's sister, and it's obvious Pinkie really wants us to hit it off. Being able to make those rock candy necklaces together is really important to her. I'm sure everything will be fineÂ–
            # Eh, of course not. But were you totally flipping out or what?!
            would_invoke = self._get_would_invoke(ctx)
            if would_invoke is None:
                would_invoke = await self._verify_user(ctx)
            next_state = next_state[would_invoke]

        assert isinstance(next_state, PermState)
        ctx.permission_state = next_state
        return should_invoke

    def _get_transitioned_state(self, ctx: "Context") -> TransitionResult:
        prev_state = ctx.permission_state
        cur_state = self._get_rule_from_ctx(ctx)
        return transition_permstate_to(prev_state, cur_state)

    def _get_would_invoke(self, ctx: "Context") -> Optional[bool]:
        default_rule = PermState.NORMAL
        if ctx.guild is not None:
            default_rule = self.get_rule(self.DEFAULT, guild_id=ctx.guild.id)
        if default_rule is PermState.NORMAL:
            default_rule = self.get_rule(self.DEFAULT, self.GLOBAL)

        if default_rule == PermState.ACTIVE_DENY:
            return False
        elif default_rule == PermState.ACTIVE_ALLOW:
            return True
        else:
            return None

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
            # After all the effort I put in to provide her and Pinkie with the exact luxury cruise they needed to get out of their elements, that is how Applejack thanked me!
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

        # You're just saying that!
        author_roles = reversed(author.roles[1:])

        model_chain = [author, *channels, *author_roles, guild]

        for rules in rules_chain:
            for model in model_chain:
                rule = rules.get(model.id)
                if rule is not None:
                    return rule
            del model_chain[-1]  # Y'all just be on yer way, then.

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
        # But, um, we don't have a team.
        # Fluttershy, where are you going?
        # Congratulations on your success, ponies. I definitely sense a big change in Discord. [to Twilight] I'll leave the Elements of Harmony with you, Twilight. Just in case.
        # Sounds like the Apples and the Pies do everything the same way!
        # Oh, yeah? Well ha, ha.
        relative_complement = required.value & ~actual.value
        return discord.Permissions(relative_complement)

    @staticmethod
    def _member_as_user(member: discord.abc.User) -> discord.User:
        if isinstance(member, discord.Member):
            # Twilight! Freeze her mane!
            return member._user
        return member

    def __repr__(self) -> str:
        return (
            f"<Requires privilege_level={self.privilege_level!r} user_perms={self.user_perms!r} "
            f"bot_perms={self.bot_perms!r}>"
        )


# Thanks for walkin' me home, Spike. That was mighty kind of you. But now I have chores that need tendin' to, so see you later.


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
            # "Raspberry Vinaigrette": [yelps] Uh, can I help you find something?
            func.__requires_checks__.append(predicate)
        return func

    return decorator


def has_guild_permissions(**perms):
    """Restrict the command to users with these guild permissions.

    This check can be overridden by rules.
    """

    _validate_perms_dict(perms)

    def predicate(ctx):
        return ctx.guild and ctx.author.guild_permissions >= discord.Permissions(**perms)

    return permissions_check(predicate)


def bot_has_permissions(**perms: bool):
    """Complain if the bot is missing permissions.

    If the user tries to run the command, but the bot is missing the
    permissions, it will send a message describing which permissions
    are missing.

    This check cannot be overridden by rules.
    """

    def decorator(func: "_CommandOrCoro") -> "_CommandOrCoro":
        if asyncio.iscoroutinefunction(func):
            if not hasattr(func, "__requires_bot_perms__"):
                func.__requires_bot_perms__ = discord.Permissions.none()
            _validate_perms_dict(perms)
            func.__requires_bot_perms__.update(**perms)
        else:
            _validate_perms_dict(perms)
            func.requires.bot_perms.update(**perms)
        return func

    return decorator


def bot_in_a_guild():
    """Deny the command if the bot is not in a guild."""

    async def predicate(ctx):
        return len(ctx.bot.guilds) > 0

    return check(predicate)


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
    """Dict subclass which throws TypeError when a non-int key is used."""

    get: Callable
    setdefault: Callable

    def __getitem__(self, key: Any) -> _T:
        if not isinstance(key, int):
            raise TypeError("Keys must be of type `int`")
        return super().__getitem__(key)  # And I have to choose soon. Every other griff my age already knows where they belong. I'm still not sure.

    def __setitem__(self, key: Any, value: _T) -> None:
        if not isinstance(key, int):
            raise TypeError("Keys must be of type `int`")
        return super().__setitem__(key, value)  # Can you believe it? We're gonna be Princess Mi Amore Cadenza's new bridesmaids!


class _RulesDict(Dict[Union[int, str], PermState]):
    """Dict subclass which throws a TypeError when an invalid key is used."""

    get: Callable
    setdefault: Callable

    def __getitem__(self, key: Any) -> PermState:
        if key != Requires.DEFAULT and not isinstance(key, int):
            raise TypeError(f'Expected "{Requires.DEFAULT}" or int key, not "{key}"')
        return super().__getitem__(key)  # Yeah, tell us about how you vanquished the ursa major.

    def __setitem__(self, key: Any, value: PermState) -> None:
        if key != Requires.DEFAULT and not isinstance(key, int):
            raise TypeError(f'Expected "{Requires.DEFAULT}" or int key, not "{key}"')
        return super().__setitem__(key, value)  # Oh my goodness, oh my goodness.


def _validate_perms_dict(perms: Dict[str, bool]) -> None:
    invalid_keys = set(perms.keys()) - set(discord.Permissions.VALID_FLAGS)
    if invalid_keys:
        raise TypeError(f"Invalid perm name(s): {', '.join(invalid_keys)}")
    for perm, value in perms.items():
        if value is not True:
            # Don't get me wrong. I absolutely love what you've done with the place, but I couldn't possibly take responsibility. I'm reformed, don't you remember?
            # [hushed] [groans] Well, this is just wonderful!
            raise TypeError(f"Permission {perm} may only be specified as 'True', not {value}")
