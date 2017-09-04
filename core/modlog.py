import discord
import os

from core import Config
from core.bot import Red
from core.utils.chat_formatting import bold
from typing import List, Union, Generator
from datetime import datetime

__all__ = [
    "Case", "get_case", "create_case", "edit_case", "get_all_casetypes",
    "is_casetype", "register_casetype", "register_casetypes",
    "get_modlog_channel", "set_modlog_channel", "toggle_case_type",
    "get_case_type_status", "get_case_type_repr", "reset_cases"
]

_DEFAULT_GLOBAL = {
    "casetypes": {}
}

_DEFAULT_GUILD = {
    "mod_log": None,
    "cases": {},
    "casetypes": {}
}

_modlog_type = type("ModLog", (object,), {})


def _register_defaults():
    _conf.register_global(**_DEFAULT_GLOBAL)
    _conf.register_guild(**_DEFAULT_GUILD)

if not os.environ.get('BUILDING_DOCS'):
    _conf = Config.get_conf(_modlog_type(), 1354799444)
    _register_defaults()


class Case:
    """A single mod log case"""

    def __init__(
            self, guild: discord.Guild, created_at: int, action_type: str,
            user: discord.User, moderator: discord.Member, case_number: int,
            reason: str=None, until: int=None,
            channel: discord.TextChannel=None, amended_by: discord.Member=None,
            modified_at: int=None, message: discord.Message=None):
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

    async def get_case_msg_content(self):
        """
        Format a case message

        :return:
            A rich embed representing a case message
        :rtype:
            discord.Embed
        """
        title = "{}".format(bold("Case #{}".format(self.case_number)))

        if self.reason:
            reason = "**Reason:** {}".format(self.reason)
        else:
            reason = \
                "**Reason:** Type [p]reason {} <reason> to add it".format(
                    self.case_number
                )

        emb = discord.Embed(title=title, description=reason)

        img_url = await get_case_type_repr(self.action_type)
        emb.set_image(url=img_url)
        moderator = "{}#{} ({})\n".format(
            self.moderator.name,
            self.moderator.discriminator,
            self.moderator.id
        )
        emb.set_author(name=moderator, icon_url=self.moderator.avatar_url)
        user = "{}#{} ({})\n".format(
            self.user.name, self.user.discriminator, self.user.id)
        emb.add_field(name="User", value=user)
        if self.until:
            start = datetime.fromtimestamp(self.created_at)
            end = datetime.fromtimestamp(self.until)
            end_fmt = end.strftime('%Y-%m-%d %H:%M:%S UTC')
            duration = end - start
            dur_fmt = _strfdelta(duration)
            until = end_fmt
            duration = dur_fmt
            emb.add_field(name="Until", value=until)
            emb.add_field(name="Duration", value=duration)

        if self.channel:
            emb.add_field(name="Channel", value=self.channel.name)
        if self.amended_by:
            amended_by = "{}#{} ({})".format(
                self.amended_by.name,
                self.amended_by.discriminator,
                self.amended_by.id
            )
            emb.add_field(name="Amended by", value=amended_by)
        if self.modified_at:
            last_modified = "{}".format(
                datetime.fromtimestamp(
                    self.modified_at
                ).strftime('%Y-%m-%d %H:%M:%S UTC')
            )
            emb.add_field(name="Last modified at", value=last_modified)

        return emb

    def to_json(self) -> dict:
        """Transform the object to a dict

        :return: The case in the form of a dict
        :rtype: dict"""
        data = {
            "case_number": self.case_number,
            "action_type": self.action_type,
            "guild": self.guild.id,
            "created_at": self.created_at,
            "user": self.user.id,
            "moderator": self.moderator.id,
            "reason": self.reason,
            "until": self.until,
            "channel": self.channel.id if hasattr(self.channel, "id") else None,
            "amended_by": self.amended_by.id if hasattr(self.amended_by, "id") else None,
            "modified_at": self.modified_at,
            "message": self.message.id if hasattr(self.message, "id") else None
        }
        return data

    @classmethod
    def from_json(cls, mod_channel: discord.TextChannel, bot: Red, data: dict):
        """Get a Case object from the provided information

        :param discord.TextChannel mod_channel:
            The mod log channel for the guild
        :param Red bot:
            The bot's instance. Needed to get the target user
        :param dict data:
            The JSON representation of the case to be gotten
        :return:
            The case object for the requested case
        :rtype: Case"""
        guild = mod_channel.guild
        message = mod_channel.get_message(data["message"])
        user = bot.get_user(data["user"])
        moderator = guild.get_member(data["moderator"])
        channel = guild.get_channel(data["channel"])
        amended_by = guild.get_member(data["amended_by"])
        return cls(
            guild=data["guild"], created_at=data["created_at"],
            action_type=data["action_type"], user=user, moderator=moderator,
            case_number=data["case_number"], reason=data["reason"],
            until=data["until"], channel=channel, amended_by=amended_by,
            modified_at=data["modified_at"], message=message
        )


async def get_case(case_number: int, guild: discord.Guild,
                   bot: Red) -> Case:
    """
    Gets the case with the associated case number

    :param int case_number: The case number for the case to get
    :param discord.Guild guild: The guild to get the case from
    :param Red bot: The bot's instance

    :return: The case associated with the case number
    :rtype: Case
    :raises RuntimeError: If there is no case for the specified number
    """
    case = await _conf.guild(guild).cases.get_attr(str(case_number))
    if case is None:
        raise RuntimeError(
            "That case does not exist for guild {}".format(guild.name)
        )
    mod_channel = await get_modlog_channel(guild)
    return Case.from_json(mod_channel, bot, case)


async def create_case(guild: discord.Guild, created_at: datetime, action_type: str,
                      user: Union[discord.User, discord.Member],
                      moderator: discord.Member, reason: str=None,
                      until: datetime=None, channel: discord.TextChannel=None
                      ) -> Case:
    """
    Creates a new case

    :param guild:
        The guild the action was taken in
    :type guild:
        discord.Guild
    :param created_at:
        The time the action occurred at
    :type created_at:
        datetime
    :param action_type:
        The type of action that was taken
    :type action_type:
        str
    :param user:
        The user target by the action
    :type user:
        discord.User or discord.Member
    :param moderator:
        The moderator who took the action
    :type moderator:
        discord.Member
    :param reason:
        The reason the action was taken
    :type reason:
        str
    :param until:
        The time the action is in effect until
    :type until:
        datetime
    :param channel:
        The channel the action was taken in
    :type channel:
        discord.TextChannel or discord.VoiceChannel
    :return:
        The newly created case
    :rtype:
        :py:class:`Case`
    :raises RuntimeError:
        If:
            the action type is not registered OR
            the mod log channel doesn't exist OR
            case creation for the action type is disabled
    """
    mod_channel = None
    if hasattr(guild, "owner"):  # Fairly arbitrary, but it doesn't really matter since we don't need the modlog channel in tests
        try:
            mod_channel = get_modlog_channel(guild)
        except RuntimeError:
            raise RuntimeError(
                "No mod log channel set for guild {}".format(guild.name)
            )
    if not await is_casetype(action_type):
        raise RuntimeError("That action type is not registered!")

    if not await get_case_type_status(action_type, guild):
        raise RuntimeError("Case creation is disabled for that action")

    next_case_number = len(await _conf.guild(guild).cases()) + 1

    case = Case(guild, int(created_at.timestamp()), action_type, user, moderator,
                next_case_number, reason, until, channel, amended_by=None,
                modified_at=None, message=None)
    if hasattr(mod_channel, "send"):  # Not going to be the case for tests
        case_emb = await case.get_case_msg_content()
        msg = await mod_channel.send(embed=case_emb)
        case.message = msg
    await _conf.guild(guild).cases.set_attr(str(next_case_number), case.to_json())
    return case


async def edit_case(case_number: int, guild: discord.Guild, bot: Red,
                    new_data: dict) -> Case:
    """
    Edits the specified case

    :param int case_number:
        The case to modify
    :param discord.Guild guild:
        The guild to edit a case for
    :param Red bot:
        The bot's instance
    :param dict new_data:
        The fields to edit
    :return:
        The edited case
    :rtype:
        :py:class:`Case`
    """
    case = await get_case(case_number, guild, bot)
    for item in list(new_data.keys()):
        setattr(case, item, new_data[item])
    case_emb = await case.get_case_msg_content()
    case.message.edit(embed=case_emb)

    await _conf.guild(guild).cases.set_attr(str(case_number), case.to_json())
    return case


async def is_casetype(case_type: str) -> bool:
    """
    Checks if the specified casetype is registered or not

    :param case_type:
        The case type to check
    :type case_type:
        str
    :return:
        :code:`True` if the case type is registered, otherwise :code:`False`
    :rtype:
        bool
    """
    case_types = await _conf.casetypes()
    return case_type in case_types


async def get_all_casetypes() -> List[str]:
    """
    Get all currently registered case types

    :return:
        A list of case type names
    :rtype:
        list
    """
    casetypes = await _conf.get_attr("casetypes")
    return list(casetypes.keys())


async def register_casetype(new_type: dict) -> bool:
    """
    Registers a new case type

    :param new_type:
        The new type to register
    :type new_type:
        dict
    :return:
        :code:`True` if registration was successful
    :rtype:
        bool
    :raises RuntimeError:
        If the case type is already registered
    """
    case_name = new_type["name"]
    default_setting = new_type["default_setting"]
    case_repr = new_type["image"]
    case_str = new_type["case_str"]
    data = {
        "default_setting": default_setting,
        "image": case_repr,
        "case_str": case_str
    }
    if await is_casetype(case_name):
        raise RuntimeError(
            "A case type with that name has already been registered!"
        )
    else:
        await _conf.casetypes.set_attr(case_name, data)
        return True


async def register_casetypes(new_types: List[dict]) -> bool:
    """
    Registers multiple case types

    :param new_types:
        The new types to register
    :type new_types:
        list
    :return:
        :code:`True` if all were registered successfully
    :rtype:
        bool
    :raises RuntimeError:
        If one of the case types couldn't be registered
    """
    for new_type in new_types:
        if not await is_casetype(new_type["name"]):
            try:
                await register_casetype(new_type)
            except RuntimeError:
                raise
    else:
        return True


async def get_modlog_channel(guild: discord.Guild
                             ) -> Union[discord.TextChannel, None]:
    """
    Get the current modlog channel

    :param guild:
        The guild to get the modlog channel for
    :type guild:
        discord.Guild
    :return:
        The channel object representing the modlog channel
    :rtype:
        discord.TextChannel or None
    :raises RuntimeError:
        If the modlog channel is not found
    """
    if hasattr(guild, "get_channel"):
        channel = guild.get_channel(await _conf.guild(guild).mod_log())
    else:
        channel = await _conf.guild(guild).mod_log()
    if channel is None:
        raise RuntimeError("Failed to get the mod log channel!")
    return channel


async def set_modlog_channel(guild: discord.Guild,
                             channel: Union[discord.TextChannel, None]) -> bool:
    """
    Changes the modlog channel

    :param guild:
        The guild to set a mod log channel for
    :type guild:
        discord.Guild
    :param channel:
        The channel to be set as modlog channel
    :type channel:
        discord.TextChannel or None
    :return:
        :code:`True` if successful
    :rtype:
        bool
    """
    await _conf.guild(guild).mod_log.set(
        channel.id if hasattr(channel, "id") else None
    )
    return True


async def toggle_case_type(case_type: str, guild: discord.Guild) -> bool:
    """
    Toggles the specified case type

    :param case_type:
        The case type to toggle
    :type case_type:
        str
    :param guild:
        The guild to toggle case type for
    :type guild:
        discord.Guild
    :return:
        The new setting for the specified case type
    :rtype:
        bool
    """
    new_setting = not await _conf.guild(guild).casetypes.get_attr(case_type)
    await _conf.guild(guild).casetypes.set_attr(case_type, new_setting)
    return new_setting


async def get_case_type_status(case_type: str, guild: discord.Guild) -> bool:
    """
    Gets the status of the specified case type

    :param case_type:
        The case type to check
    :type case_type:
        str
    :param guild:
        The guild to check the setting for
    :type guild:
        discord.Guild
    :return:
        The current setting for the specified case type
    :rtype:
        bool
    :raises RuntimeError:
        If the specified case type is not registered
    """
    if await is_casetype(case_type):
        default = await _conf.casetypes.get_attr(case_type)
        return await _conf.guild(guild).casetypes.get_attr(case_type, default)
    else:
        raise RuntimeError("That case type is not registered!")


async def get_case_type_repr(case_type: str) -> str:
    """
    Gets the image representation of a case type

    :param case_type:
        The case type to get the representation of
    :type case_type:
        str
    :return:
        The case type's representation
    :rtype:
        str
    """
    return await _conf.casetypes.get_attr(case_type, resolve=False).image()


async def reset_cases(guild: discord.Guild) -> bool:
    """
    Wipes all modlog cases for the specified guild

    :param guild:
        The guild to reset cases for
    :type guild:
        discord.Guild
    :return:
        :code:`True` if successful
    :rtype:
        bool
    """
    await _conf.guild(guild).cases.set({})
    return True


def _strfdelta(delta):
    s = []
    if delta.days:
        ds = '%i day' % delta.days
        if delta.days > 1:
            ds += 's'
        s.append(ds)
    hrs, rem = divmod(delta.seconds, 60*60)
    if hrs:
        hs = '%i hr' % hrs
        if hrs > 1:
            hs += 's'
        s.append(hs)
    mins, secs = divmod(rem, 60)
    if mins:
        s.append('%i min' % mins)
    if secs:
        s.append('%i sec' % secs)
    return ' '.join(s)
