from datetime import datetime
from typing import List, Union, Optional, cast

import discord

from redbot.core import Config
from redbot.core.bot import Red

from .utils.common_filters import (
    filter_invites,
    filter_mass_mentions,
    filter_urls,
    escape_spoilers,
)

__all__ = [
    "Case",
    "CaseType",
    "get_next_case_number",
    "get_case",
    "get_all_cases",
    "get_cases_for_member",
    "create_case",
    "get_casetype",
    "get_all_casetypes",
    "register_casetype",
    "register_casetypes",
    "get_modlog_channel",
    "set_modlog_channel",
    "reset_cases",
]

_conf: Optional[Config] = None

_CASETYPES = "CASETYPES"
_CASES = "CASES"
_SCHEMA_VERSION = 2


async def _init():
    global _conf
    _conf = Config.get_conf(None, 1354799444, cog_name="ModLog")
    _conf.register_guild(mod_log=None, casetypes={}, schema_version=1)
    _conf.init_custom(_CASETYPES, 1)
    _conf.init_custom(_CASES, 2)
    _conf.register_custom(
        _CASETYPES, default_setting=None, image=None, case_str=None, audit_type=None
    )
    _conf.register_custom(
        _CASES,
        case_number=None,
        action_type=None,
        guild=None,
        created_at=None,
        user=None,
        moderator=None,
        reason=None,
        until=None,
        channel=None,
        amended_by=None,
        modified_at=None,
        message=None,
    )
    await _migrate_config(from_version=await _conf.schema_version(), to_version=_SCHEMA_VERSION)


async def _migrate_config(from_version: int, to_version: int):
    if from_version == to_version:
        return
    elif from_version < to_version:
        # casetypes go from GLOBAL -> casetypes to CASETYPES
        all_casetypes = await _conf.get_raw("casetypes", default={})
        if all_casetypes:
            await _conf.custom(_CASETYPES).set(all_casetypes)

        # cases go from GUILD -> guild_id -> cases to CASES -> guild_id -> cases
        all_guild_data = await _conf.all_guilds()
        all_cases = {}
        for guild_id, guild_data in all_guild_data.items():
            guild_cases = guild_data.pop("cases", None)
            if guild_cases:
                all_cases[str(guild_id)] = guild_cases
        await _conf.custom(_CASES).set(all_cases)

        # new schema is now in place
        await _conf.schema_version.set(_SCHEMA_VERSION)

        # migration done, now let's delete all the old stuff
        await _conf.clear_raw("casetypes")
        for guild_id in all_guild_data:
            await _conf.guild(cast(discord.Guild, discord.Object(id=guild_id))).clear_raw("cases")


class Case:
    """A single mod log case"""

    def __init__(
        self,
        bot: Red,
        guild: discord.Guild,
        created_at: int,
        action_type: str,
        user: Union[discord.User, int],
        moderator: discord.User,
        case_number: int,
        reason: str = None,
        until: int = None,
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel, int]] = None,
        amended_by: Optional[discord.User] = None,
        modified_at: Optional[int] = None,
        message: Optional[discord.Message] = None,
    ):
        self.bot = bot
        self.guild = guild
        self.created_at = created_at
        self.action_type = action_type
        self.user = user
        self.moderator = moderator
        self.reason = reason
        self.until = until
        self.channel = channel
        self.amended_by = amended_by
        self.modified_at = modified_at
        self.case_number = case_number
        self.message = message

    async def edit(self, data: dict):
        """
        Edits a case

        Parameters
        ----------
        data: dict
            The attributes to change

        """
        for item in list(data.keys()):
            setattr(self, item, data[item])

        await _conf.custom(_CASES, str(self.guild.id), str(self.case_number)).set(self.to_json())
        self.bot.dispatch("modlog_case_edit", self)

    async def message_content(self, embed: bool = True):
        """
        Format a case message

        Parameters
        ----------
        embed: bool
            Whether or not to get an embed

        Returns
        -------
        discord.Embed or `str`
            A rich embed or string representing a case message

        """
        casetype = await get_casetype(self.action_type)
        title = "{}".format(
            "Case #{} | {} {}".format(self.case_number, casetype.case_str, casetype.image)
        )

        if self.reason:
            reason = "**Reason:** {}".format(self.reason)
        else:
            reason = "**Reason:** Use `[p]reason {} <reason>` to add it".format(self.case_number)

        if self.moderator is not None:
            moderator = escape_spoilers(f"{self.moderator} ({self.moderator.id})")
        else:
            moderator = "Unknown"
        until = None
        duration = None
        if self.until:
            start = datetime.fromtimestamp(self.created_at)
            end = datetime.fromtimestamp(self.until)
            end_fmt = end.strftime("%Y-%m-%d %H:%M:%S")
            duration = end - start
            dur_fmt = _strfdelta(duration)
            until = end_fmt
            duration = dur_fmt

        amended_by = None
        if self.amended_by:
            amended_by = escape_spoilers(
                "{}#{} ({})".format(
                    self.amended_by.name, self.amended_by.discriminator, self.amended_by.id
                )
            )

        last_modified = None
        if self.modified_at:
            last_modified = "{}".format(
                datetime.fromtimestamp(self.modified_at).strftime("%Y-%m-%d %H:%M:%S")
            )

        if isinstance(self.user, int):
            user = f"Deleted User#0000 ({self.user})"
            avatar_url = None
        else:
            user = escape_spoilers(
                filter_invites(f"{self.user} ({self.user.id})")
            )  # Invites and spoilers get rendered even in embeds.
            avatar_url = self.user.avatar_url

        if embed:
            emb = discord.Embed(title=title, description=reason)

            if avatar_url is not None:
                emb.set_author(name=user, icon_url=avatar_url)
            emb.add_field(name="Moderator", value=moderator, inline=False)
            if until and duration:
                emb.add_field(name="Until", value=until)
                emb.add_field(name="Duration", value=duration)

            if isinstance(self.channel, int):
                emb.add_field(name="Channel", value=f"{self.channel} (deleted)", inline=False)
            elif self.channel is not None:
                emb.add_field(name="Channel", value=self.channel.name, inline=False)
            if amended_by:
                emb.add_field(name="Amended by", value=amended_by)
            if last_modified:
                emb.add_field(name="Last modified at", value=last_modified)
            emb.timestamp = datetime.fromtimestamp(self.created_at)
            return emb
        else:
            user = filter_mass_mentions(filter_urls(user))  # Further sanitization outside embeds
            case_text = ""
            case_text += "{}\n".format(title)
            case_text += "**User:** {}\n".format(user)
            case_text += "**Moderator:** {}\n".format(moderator)
            case_text += "{}\n".format(reason)
            if until and duration:
                case_text += "**Until:** {}\n**Duration:** {}\n".format(until, duration)
            if self.channel:
                case_text += "**Channel**: {}\n".format(self.channel.name)
            if amended_by:
                case_text += "**Amended by:** {}\n".format(amended_by)
            if last_modified:
                case_text += "**Last modified at:** {}\n".format(last_modified)
            return case_text.strip()

    def to_json(self) -> dict:
        """Transform the object to a dict

        Returns
        -------
        dict
            The case in the form of a dict

        """
        if self.moderator is not None:
            mod = self.moderator.id
        else:
            mod = None
        if isinstance(self.user, int):
            user_id = self.user
        else:
            user_id = self.user.id
        data = {
            "action_type": self.action_type,
            "guild": self.guild.id,
            "created_at": self.created_at,
            "user": user_id,
            "moderator": mod,
            "reason": self.reason,
            "until": self.until,
            "channel": self.channel.id if hasattr(self.channel, "id") else None,
            "amended_by": self.amended_by.id if hasattr(self.amended_by, "id") else None,
            "modified_at": self.modified_at,
            "message": self.message.id if hasattr(self.message, "id") else None,
        }
        return data

    @classmethod
    async def from_json(
        cls, mod_channel: discord.TextChannel, bot: Red, case_number: int, data: dict, **kwargs
    ):
        """Get a Case object from the provided information

        Parameters
        ----------
        mod_channel: discord.TextChannel
            The mod log channel for the guild
        bot: Red
            The bot's instance. Needed to get the target user
        case_number: int
            The case's number.
        data: dict
            The JSON representation of the case to be gotten
        **kwargs
            Extra attributes for the Case instance which override values
            in the data dict. These should be complete objects and not
            IDs, where possible.

        Returns
        -------
        Case
            The case object for the requested case

        Raises
        ------
        `discord.NotFound`
            The user the case is for no longer exists
        `discord.Forbidden`
            Cannot read message history to fetch the original message.
        `discord.HTTPException`
            A generic API issue
        """
        guild = kwargs.get("guild") or mod_channel.guild

        message = kwargs.get("message")
        if message is None:
            message_id = data.get("message")
            if message_id is not None:
                try:
                    message = discord.utils.get(bot.cached_messages, id=message_id)
                except AttributeError:
                    # bot.cached_messages didn't exist prior to discord.py 1.1.0
                    message = None
                if message is None:
                    try:
                        message = await mod_channel.fetch_message(message_id)
                    except (discord.NotFound, AttributeError):
                        message = None
            else:
                message = None

        user_objects = {"user": None, "moderator": None, "amended_by": None}
        for user_key in tuple(user_objects):
            user_object = kwargs.get(user_key)
            if user_object is None:
                user_id = data.get(user_key)
                if user_id is None:
                    user_object = None
                else:
                    user_object = bot.get_user(user_id)
                    if user_object is None:
                        try:
                            user_object = await bot.fetch_user(user_id)
                        except discord.NotFound:
                            user_object = user_id
            user_objects[user_key] = user_object

        channel = kwargs.get("channel") or guild.get_channel(data["channel"]) or data["channel"]
        case_guild = kwargs.get("guild") or bot.get_guild(data["guild"])
        return cls(
            bot=bot,
            guild=case_guild,
            created_at=data["created_at"],
            action_type=data["action_type"],
            case_number=case_number,
            reason=data["reason"],
            until=data["until"],
            channel=channel,
            modified_at=data["modified_at"],
            message=message,
            **user_objects,
        )


class CaseType:
    """
    A single case type

    Attributes
    ----------
    name: str
        The name of the case
    default_setting: bool
        Whether the case type should be on (if `True`)
        or off (if `False`) by default
    image: str
        The emoji to use for the case type (for example, :boot:)
    case_str: str
        The string representation of the case (example: Ban)
    audit_type: `str`, optional
        The action type of the action as it would appear in the
        audit log
    """

    def __init__(
        self,
        name: str,
        default_setting: bool,
        image: str,
        case_str: str,
        audit_type: Optional[str] = None,
        guild: Optional[discord.Guild] = None,
    ):
        self.name = name
        self.default_setting = default_setting
        self.image = image
        self.case_str = case_str
        self.audit_type = audit_type
        self.guild = guild

    async def to_json(self):
        """Transforms the case type into a dict and saves it"""
        data = {
            "default_setting": self.default_setting,
            "image": self.image,
            "case_str": self.case_str,
            "audit_type": self.audit_type,
        }
        await _conf.custom(_CASETYPES, self.name).set(data)

    async def is_enabled(self) -> bool:
        """
        Determines if the case is enabled.
        If the guild is not set, this will always return False

        Returns
        -------
        bool:
            True if the guild is set and the casetype is enabled for the guild

            False if the guild is not set or if the guild is set and the type
            is disabled
        """
        if not self.guild:
            return False
        return await _conf.guild(self.guild).casetypes.get_raw(
            self.name, default=self.default_setting
        )

    async def set_enabled(self, enabled: bool):
        """
        Sets the case as enabled or disabled

        Parameters
        ----------
        enabled: bool
            True if the case should be enabled, otherwise False"""
        if not self.guild:
            return
        await _conf.guild(self.guild).casetypes.set_raw(self.name, value=enabled)

    @classmethod
    def from_json(cls, name: str, data: dict, **kwargs):
        """

        Parameters
        ----------
        name : str
            The casetype's name.
        data : dict
            The JSON data to create an instance from
        **kwargs
            Values for other attributes of the instance

        Returns
        -------
        CaseType

        """
        return cls(name=name, **data, **kwargs)


async def get_next_case_number(guild: discord.Guild) -> int:
    """
    Gets the next case number

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the next case number for

    Returns
    -------
    int
        The next case number

    """
    case_numbers = (await _conf.custom(_CASES, guild.id).all()).keys()
    if not case_numbers:
        return 1
    else:
        return int(max(case_numbers)) + 1


async def get_case(case_number: int, guild: discord.Guild, bot: Red) -> Case:
    """
    Gets the case with the associated case number

    Parameters
    ----------
    case_number: int
        The case number for the case to get
    guild: discord.Guild
        The guild to get the case from
    bot: Red
        The bot's instance

    Returns
    -------
    Case
        The case associated with the case number

    Raises
    ------
    RuntimeError
        If there is no case for the specified number

    """
    try:
        case = await _conf.custom(_CASES, str(guild.id), str(case_number)).all()
    except KeyError as e:
        raise RuntimeError("That case does not exist for guild {}".format(guild.name)) from e
    mod_channel = await get_modlog_channel(guild)
    return await Case.from_json(mod_channel, bot, case_number, case)


async def get_all_cases(guild: discord.Guild, bot: Red) -> List[Case]:
    """
    Gets all cases for the specified guild

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the cases from
    bot: Red
        The bot's instance

    Returns
    -------
    list
        A list of all cases for the guild

    """
    cases = await _conf.custom(_CASES, str(guild.id)).all()
    mod_channel = await get_modlog_channel(guild)
    return [
        await Case.from_json(mod_channel, bot, case_number, case_data)
        for case_number, case_data in cases.items()
    ]


async def get_cases_for_member(
    guild: discord.Guild, bot: Red, *, member: discord.Member = None, member_id: int = None
) -> List[Case]:
    """
    Gets all cases for the specified member or member id in a guild.

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the cases from
    bot: Red
        The bot's instance
    member: `discord.Member`
        The member to get cases about
    member_id: int
        The id of the member to get cases about

    Returns
    -------
    list
        A list of all matching cases.

    Raises
    ------
    ValueError
        If at least one of member or member_id is not provided
    `discord.Forbidden`
        The bot does not have permission to fetch the modlog message which was sent.
    `discord.HTTPException`
        Fetching the user failed.
    """

    cases = await _conf.custom(_CASES, str(guild.id)).all()

    if not (member_id or member):
        raise ValueError("Expected a member or a member id to be provided.") from None

    if not member_id:
        member_id = member.id

    if not member:
        member = bot.get_user(member_id)
        if not member:
            try:
                member = await bot.fetch_user(member_id)
            except discord.NotFound:
                member = member_id

    try:
        modlog_channel = await get_modlog_channel(guild)
    except RuntimeError:
        modlog_channel = None

    cases = [
        await Case.from_json(modlog_channel, bot, case_number, case_data, user=member, guild=guild)
        for case_number, case_data in cases.items()
        if case_data["user"] == member_id
    ]

    return cases


async def create_case(
    bot: Red,
    guild: discord.Guild,
    created_at: datetime,
    action_type: str,
    user: Union[discord.User, discord.Member],
    moderator: Optional[Union[discord.User, discord.Member]] = None,
    reason: Optional[str] = None,
    until: Optional[datetime] = None,
    channel: Optional[discord.TextChannel] = None,
) -> Optional[Case]:
    """
    Creates a new case.

    This fires an event :code:`on_modlog_case_create`

    Parameters
    ----------
    bot: Red
        The bot object
    guild: discord.Guild
        The guild the action was taken in
    created_at: datetime
        The time the action occurred at
    action_type: str
        The type of action that was taken
    user: Union[discord.User, discord.Member]
        The user target by the action
    moderator: Optional[Union[discord.User, discord.Member]]
        The moderator who took the action
    reason: Optional[str]
        The reason the action was taken
    until: Optional[datetime]
        The time the action is in effect until
    channel: Optional[discord.TextChannel]
        The channel the action was taken in
    """
    case_type = await get_casetype(action_type, guild)
    if case_type is None:
        return

    if not await case_type.is_enabled():
        return

    if user == bot.user:
        return

    next_case_number = await get_next_case_number(guild)

    case = Case(
        bot,
        guild,
        int(created_at.timestamp()),
        action_type,
        user,
        moderator,
        next_case_number,
        reason,
        int(until.timestamp()) if until else None,
        channel,
        amended_by=None,
        modified_at=None,
        message=None,
    )
    await _conf.custom(_CASES, str(guild.id), str(next_case_number)).set(case.to_json())
    bot.dispatch("modlog_case_create", case)
    return case


async def get_casetype(name: str, guild: Optional[discord.Guild] = None) -> Optional[CaseType]:
    """
    Gets the case type

    Parameters
    ----------
    name: str
        The name of the case type to get
    guild: Optional[discord.Guild]
        If provided, sets the case type's guild attribute to this guild

    Returns
    -------
    Optional[CaseType]
    """
    try:
        data = await _conf.custom(_CASETYPES, name).all()
    except KeyError:
        return
    else:
        casetype = CaseType.from_json(name, data)
        casetype.guild = guild
        return casetype


async def get_all_casetypes(guild: discord.Guild = None) -> List[CaseType]:
    """
    Get all currently registered case types

    Returns
    -------
    list
        A list of case types

    """
    return [
        CaseType.from_json(name, data, guild=guild)
        for name, data in await _conf.custom(_CASETYPES).all()
    ]


async def register_casetype(
    name: str, default_setting: bool, image: str, case_str: str, audit_type: str = None
) -> CaseType:
    """
    Registers a case type. If the case type exists and
    there are differences between the values passed and
    what is stored already, the case type will be updated
    with the new values

    Parameters
    ----------
    name: str
        The name of the case
    default_setting: bool
        Whether the case type should be on (if `True`)
        or off (if `False`) by default
    image: str
        The emoji to use for the case type (for example, :boot:)
    case_str: str
        The string representation of the case (example: Ban)
    audit_type: `str`, optional
        The action type of the action as it would appear in the
        audit log

    Returns
    -------
    CaseType
        The case type that was registered

    Raises
    ------
    RuntimeError
        If the case type is already registered
    TypeError:
        If a parameter is missing
    ValueError
        If a parameter's value is not valid
    AttributeError
        If the audit_type is not an attribute of `discord.AuditLogAction`

    """
    if not isinstance(name, str):
        raise ValueError("The 'name' is not a string! Check the value!")
    if not isinstance(default_setting, bool):
        raise ValueError("'default_setting' needs to be a bool!")
    if not isinstance(image, str):
        raise ValueError("The 'image' is not a string!")
    if not isinstance(case_str, str):
        raise ValueError("The 'case_str' is not a string!")
    if audit_type is not None:
        if not isinstance(audit_type, str):
            raise ValueError("The 'audit_type' is not a string!")
        try:
            getattr(discord.AuditLogAction, audit_type)
        except AttributeError:
            raise
    ct = await get_casetype(name)
    if ct is None:
        casetype = CaseType(name, default_setting, image, case_str, audit_type)
        await casetype.to_json()
        return casetype
    else:
        # Case type exists, so check for differences
        # If no differences, raise RuntimeError
        changed = False
        if ct.default_setting != default_setting:
            ct.default_setting = default_setting
            changed = True
        if ct.image != image:
            ct.image = image
            changed = True
        if ct.case_str != case_str:
            ct.case_str = case_str
            changed = True
        if ct.audit_type != audit_type:
            ct.audit_type = audit_type
            changed = True
        if changed:
            await ct.to_json()
            return ct
        else:
            raise RuntimeError("That case type is already registered!")


async def register_casetypes(new_types: List[dict]) -> List[CaseType]:
    """
    Registers multiple case types

    Parameters
    ----------
    new_types: list
        The new types to register

    Returns
    -------
    bool
        `True` if all were registered successfully

    Raises
    ------
    KeyError
    ValueError
    AttributeError

    See Also
    --------
    redbot.core.modlog.register_casetype

    """
    type_list = []
    for new_type in new_types:
        try:
            ct = await register_casetype(**new_type)
        except RuntimeError:
            # We pass here because RuntimeError signifies the case was
            # already registered.
            pass
        else:
            type_list.append(ct)
    else:
        return type_list


async def get_modlog_channel(guild: discord.Guild) -> discord.TextChannel:
    """
    Get the current modlog channel.

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the modlog channel for.

    Returns
    -------
    `discord.TextChannel`
        The channel object representing the modlog channel.

    Raises
    ------
    RuntimeError
        If the modlog channel is not found.

    """
    if hasattr(guild, "get_channel"):
        channel = guild.get_channel(await _conf.guild(guild).mod_log())
    else:
        # For unit tests only
        channel = await _conf.guild(guild).mod_log()
    if channel is None:
        raise RuntimeError("Failed to get the mod log channel!")
    return channel


async def set_modlog_channel(
    guild: discord.Guild, channel: Union[discord.TextChannel, None]
) -> bool:
    """
    Changes the modlog channel

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to set a mod log channel for
    channel: `discord.TextChannel` or `None`
        The channel to be set as modlog channel

    Returns
    -------
    bool
        `True` if successful

    """
    await _conf.guild(guild).mod_log.set(channel.id if hasattr(channel, "id") else None)
    return True


async def reset_cases(guild: discord.Guild) -> None:
    """
    Wipes all modlog cases for the specified guild

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to reset cases for

    """
    await _conf.custom(_CASES, str(guild.id)).clear()


def _strfdelta(delta):
    s = []
    if delta.days:
        ds = "%i day" % delta.days
        if delta.days > 1:
            ds += "s"
        s.append(ds)
    hrs, rem = divmod(delta.seconds, 60 * 60)
    if hrs:
        hs = "%i hr" % hrs
        if hrs > 1:
            hs += "s"
        s.append(hs)
    mins, secs = divmod(rem, 60)
    if mins:
        s.append("%i min" % mins)
    if secs:
        s.append("%i sec" % secs)
    return " ".join(s)
