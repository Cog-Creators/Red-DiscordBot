from datetime import datetime
from typing import List, Union

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
    "create_case",
    "get_casetype",
    "get_all_casetypes",
    "register_casetype",
    "register_casetypes",
    "get_modlog_channel",
    "set_modlog_channel",
    "reset_cases",
]

_DEFAULT_GLOBAL = {"casetypes": {}}

_DEFAULT_GUILD = {"mod_log": None, "cases": {}, "casetypes": {}}

_conf: Config = None


def _init():
    global _conf
    _conf = Config.get_conf(None, 1354799444, cog_name="ModLog")
    _conf.register_global(**_DEFAULT_GLOBAL)
    _conf.register_guild(**_DEFAULT_GUILD)


class Case:
    """A single mod log case"""

    def __init__(
        self,
        bot: Red,
        guild: discord.Guild,
        created_at: int,
        action_type: str,
        user: discord.User,
        moderator: discord.Member,
        case_number: int,
        reason: str = None,
        until: int = None,
        channel: discord.TextChannel = None,
        amended_by: discord.Member = None,
        modified_at: int = None,
        message: discord.Message = None,
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

        await _conf.guild(self.guild).cases.set_raw(str(self.case_number), value=self.to_json())
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
            moderator = escape_spoilers(
                "{}#{} ({})\n".format(
                    self.moderator.name, self.moderator.discriminator, self.moderator.id
                )
            )
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

        user = escape_spoilers(
            filter_invites(
                "{}#{} ({})\n".format(self.user.name, self.user.discriminator, self.user.id)
            )
        )  # Invites and spoilers get rendered even in embeds.
        if embed:
            emb = discord.Embed(title=title, description=reason)

            emb.set_author(name=user, icon_url=self.user.avatar_url)
            emb.add_field(name="Moderator", value=moderator, inline=False)
            if until and duration:
                emb.add_field(name="Until", value=until)
                emb.add_field(name="Duration", value=duration)

            if self.channel:
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
        data = {
            "case_number": self.case_number,
            "action_type": self.action_type,
            "guild": self.guild.id,
            "created_at": self.created_at,
            "user": self.user.id,
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
    async def from_json(cls, mod_channel: discord.TextChannel, bot: Red, data: dict):
        """Get a Case object from the provided information

        Parameters
        ----------
        mod_channel: discord.TextChannel
            The mod log channel for the guild
        bot: Red
            The bot's instance. Needed to get the target user
        data: dict
            The JSON representation of the case to be gotten

        Returns
        -------
        Case
            The case object for the requested case

        """
        guild = mod_channel.guild
        message = await mod_channel.get_message(data["message"])
        user = await bot.get_user_info(data["user"])
        moderator = guild.get_member(data["moderator"])
        channel = guild.get_channel(data["channel"])
        amended_by = guild.get_member(data["amended_by"])
        case_guild = bot.get_guild(data["guild"])
        return cls(
            bot=bot,
            guild=case_guild,
            created_at=data["created_at"],
            action_type=data["action_type"],
            user=user,
            moderator=moderator,
            case_number=data["case_number"],
            reason=data["reason"],
            until=data["until"],
            channel=channel,
            amended_by=amended_by,
            modified_at=data["modified_at"],
            message=message,
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
        audit_type: str = None,
        guild: discord.Guild = None,
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
        await _conf.casetypes.set_raw(self.name, value=data)

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
    def from_json(cls, data: dict):
        """

        Parameters
        ----------
        data: dict
            The data to create an instance from

        Returns
        -------
        CaseType

        """
        return cls(**data)


async def get_next_case_number(guild: discord.Guild) -> str:
    """
    Gets the next case number

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to get the next case number for

    Returns
    -------
    str
        The next case number

    """
    cases = sorted((await _conf.guild(guild).get_raw("cases")), key=lambda x: int(x), reverse=True)
    return str(int(cases[0]) + 1) if cases else "1"


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
        case = await _conf.guild(guild).cases.get_raw(str(case_number))
    except KeyError as e:
        raise RuntimeError("That case does not exist for guild {}".format(guild.name)) from e
    mod_channel = await get_modlog_channel(guild)
    return await Case.from_json(mod_channel, bot, case)


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
    cases = await _conf.guild(guild).get_raw("cases")
    case_numbers = list(cases.keys())
    case_list = []
    for case in case_numbers:
        case_list.append(await get_case(case, guild, bot))
    return case_list


async def create_case(
    bot: Red,
    guild: discord.Guild,
    created_at: datetime,
    action_type: str,
    user: Union[discord.User, discord.Member],
    moderator: discord.Member = None,
    reason: str = None,
    until: datetime = None,
    channel: discord.TextChannel = None,
) -> Union[Case, None]:
    """
    Creates a new case.

    This fires an event :code:`on_modlog_case_create`

    Parameters
    ----------
    bot: `Red`
        The bot object
    guild: `discord.Guild`
        The guild the action was taken in
    created_at: datetime
        The time the action occurred at
    action_type: str
        The type of action that was taken
    user: `discord.User` or `discord.Member`
        The user target by the action
    moderator: `discord.Member`
        The moderator who took the action
    reason: str
        The reason the action was taken
    until: datetime
        The time the action is in effect until
    channel: `discord.TextChannel` or `discord.VoiceChannel`
        The channel the action was taken in
    """
    case_type = await get_casetype(action_type, guild)
    if case_type is None:
        return None

    if not await case_type.is_enabled():
        return None

    if user == bot.user:
        return None

    next_case_number = int(await get_next_case_number(guild))

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
    await _conf.guild(guild).cases.set_raw(str(next_case_number), value=case.to_json())
    bot.dispatch("modlog_case_create", case)
    return case


async def get_casetype(name: str, guild: discord.Guild = None) -> Union[CaseType, None]:
    """
    Gets the case type

    Parameters
    ----------
    name: str
        The name of the case type to get
    guild: discord.Guild
        If provided, sets the case type's guild attribute to this guild

    Returns
    -------
    CaseType or None
    """
    casetypes = await _conf.get_raw("casetypes")
    if name in casetypes:
        data = casetypes[name]
        data["name"] = name
        casetype = CaseType.from_json(data)
        casetype.guild = guild
        return casetype
    else:
        return None


async def get_all_casetypes(guild: discord.Guild = None) -> List[CaseType]:
    """
    Get all currently registered case types

    Returns
    -------
    list
        A list of case types

    """
    casetypes = await _conf.get_raw("casetypes", default={})
    typelist = []
    for ct in casetypes.keys():
        data = casetypes[ct]
        data["name"] = ct
        casetype = CaseType.from_json(data)
        casetype.guild = guild
        typelist.append(casetype)
    return typelist


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
    RuntimeError
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
            raise
        except ValueError:
            raise
        except AttributeError:
            raise
        except TypeError:
            raise
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


async def reset_cases(guild: discord.Guild) -> bool:
    """
    Wipes all modlog cases for the specified guild

    Parameters
    ----------
    guild: `discord.Guild`
        The guild to reset cases for

    Returns
    -------
    bool
        `True` if successful

    """
    await _conf.guild(guild).cases.set({})
    return True


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
