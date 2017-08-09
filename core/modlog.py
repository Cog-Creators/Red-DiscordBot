import discord
from core import Config
from core.utils.chat_formatting import bold
from collections import namedtuple
from typing import List
from datetime import datetime

__all__ = [
    "get_case", "create_case", "edit_case", "is_casetype",
    "register_casetype", "register_casetypes"
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


_conf = Config.get_conf(_modlog_type(), 1354799444)


def _register_defaults():
    _conf.register_global(**_DEFAULT_GLOBAL)
    _conf.register_guild(**_DEFAULT_GUILD)


_register_defaults()


def get_case(case_number: int) -> None:
    """
    Gets the case with the associated case number
    :param int case_number: The case number for the case to get
    :return: the case associated with the case number
    :rtype: Case
    :raises RuntimeError: if there is no case for the specified number
    """
    pass


async def create_case(guild: discord.Guild, created_at: datetime,
                      action_type: str, user: discord.User,
                      moderator: discord.Member, reason: str=None,
                      until: datetime=None, channel: discord.TextChannel=None
                      ) -> bool:
    """
    Creates a new case
    :param discord.Guild guild: The guild the action was taken in
    :param datetime created_at: The time the action occurred at
    :param str action_type: The type of action that was taken
    :param discord.abc.User user: The user target by the action
    :param discord.Member moderator: The moderator who took the action
    :param str reason: The reason the action was taken
    :param datetime until: The time the action is in effect until
    :param discord.TextChannel channel: The channel the action was taken in
    :return: True if successful
    :rtype: bool
    :raises RuntimeError: if the action type is not registered or the mod log channel doesn't exist
    """
    data = {
        "guild": guild.id,
        "created_at": created_at,
        "action_type": action_type,
        "user": user.id,
        "moderator": moderator.id,
        "reason": reason,
        "until": until,
        "channel": channel.id if hasattr(channel, "id") else None,
        "message": None,
        "modified_at": None
    }

    try:
        mod_channel = get_modlog_channel(guild)
    except RuntimeError:
        raise
    if not is_casetype(action_type):
        raise RuntimeError("That action type is not registered!")

    next_case_number = len(_conf.guild(guild).cases()) + 1
    data["case_number"] = next_case_number
    to_send = _format_case_msg(
        next_case_number, action_type, user,
        moderator, int(created_at.timestamp()), int(until.timestamp()),
        None, reason, None)
    msg = await mod_channel.send(to_send)
    data["message"] = msg.id
    await _conf.guild(guild).cases.set_attr(str(next_case_number), data)
    return True


def _format_case_msg(
        case_number: int, action_type: str, user: discord.User,
        moderator: discord.Member, created_at: int, until: int,
        amended_by: discord.Member=None, reason: str=None,
        modified_at: int=None) -> str:
    """
    Format a case message from info provided. Should never be called
        outside of :func create_case: and :func edit_case:
    :param case_number:
    :param action_type:
    :param user:
    :param moderator:
    :param created_at:
    :param until:
    :param amended_by:
    :param reason:
    :param modified_at:
    :return:
    """
    case_type = ""
    case_type += "{} | {}\n".format(
        bold("Case #{}".format(case_number)),
        get_case_type_repr(action_type))
    case_type += "**User:** {}#{} ({})\n".format(
        user.name, user.discriminator, user.id)
    case_type += "**Moderator:** {}#{} ({})\n".format(
        moderator.name, moderator.discriminator, moderator.id
    )

    if until:
        start = datetime.fromtimestamp(created_at)
        end = datetime.fromtimestamp(until)
        end_fmt = end.strftime('%Y-%m-%d %H:%M:%S UTC')
        duration = end - start
        dur_fmt = _strfdelta(duration)
        case_type += ("**Until:** {}\n"
                      "**Duration:** {}\n").format(end_fmt, dur_fmt)
    if amended_by:
        case_type += "**Amended by:** {}#{} ({})\n".format(
            amended_by.name, amended_by.discriminator, amended_by.id)
    if modified_at:
        case_type += "**Last modified**: {}\n".format(
            datetime.fromtimestamp(
                modified_at
            ).strftime('%Y-%m-%d %H:%M:%S UTC')
        )
    if reason:
        case_type += "**Reason:** {}".format(reason)
    else:
        case_type += "**Reason:** Type [p]reason {} <reason> to add it".format(case)
    return case_type


async def edit_case(case_number: int, new_data: dict) -> Case:
    """
    Edits the specified case
    :param int case_number: The case to modify
    :param dict new_data: The fields to edit
    :return: The edited case
    :rtype: Case
    """
    pass


def is_casetype(case_type: str) -> bool:
    """
    Checks if the specified casetype is registered or not
    :param str case_type: The case type to check
    :return: True if the specified case type is registered otherwise False
    :rtype: bool
    """
    return case_type in _conf.casetypes()


async def register_casetype(new_type: dict) -> bool:
    """
    Registers a new case type
    :param dict new_type: The new type to register
    :return: True if registration was successful
    :rtype: bool
    :raises RuntimeError: if the case type is already registered
    """
    case_name = new_type["name"]
    default_setting = new_type["default"]
    case_repr = new_type["type_image"]
    data = {
        "default_setting": default_setting,
        "image": case_repr
    }
    if is_casetype(case_name):
        raise RuntimeError(
            "A case type with that name has already been registered!"
        )
    else:
        await _conf.casetypes.setattr(case_name, default_setting)
        return True


async def register_casetypes(new_types: List[dict]) -> bool:
    """
    Registers multiple case types
    :param list new_types: The new types to register
    :return: True if all were registered successfully
    :rtype: bool
    :raises RuntimeError: if one of the case types couldn't be registered
    """
    for new_type in new_types:
        try:
            await register_casetype(new_type)
        except RuntimeError:
            raise
    else:
        return True


def get_modlog_channel(guild: discord.Guild) -> discord.TextChannel:
    """
    Get the current modlog channel
    :param discord.Guild guild: the guild to get the modlog channel for
    :return: The channel object representing the modlog channel
    :rtype: discord.Guild
    :raises RuntimeError: if the modlog channel is not found
        (i.e. set to None or channel has been deleted and not changed)
    """
    channel = guild.get_channel(_conf.guild(guild))
    if channel is None:
        raise RuntimeError("Failed to get the mod log channel!")
    return channel


async def set_modlog_channel(channel: discord.TextChannel) -> bool:
    """
    Changes the modlog channel
    :param discord.TextChannel channel: the channel to be set as modlog channel
    :return: True if successful
    :rtype: bool
    """
    await _conf.guild(channel.guild).mod_log.set(channel.id)
    return True


async def toggle_case_type(case_type: str, guild: discord.Guild) -> bool:
    """
    Toggles the specified case type
    :param str case_type: The case type to toggle
    :param discord.Guild guild: The guild to toggle case type for
    :return: The new setting for the specified case type
    :rtype: bool
    """
    new_setting = not _conf.guild(guild).casetypes.get_attr(case_type)
    await _conf.guild(guild).casetypes.set_attr(case_type, new_setting)
    return new_setting


def get_case_type_status(case_type: str, guild: discord.Guild) -> bool:
    """
    Gets the status of the specified case type
    :param str case_type: The case type to check
    :param discord.Guild guild: The guild to check
    :return: The current setting for the specified case type
    :raises RuntimeError: if the specified case type is not registered
    """
    if is_casetype(case_type):
        default = _conf.casetypes.get_attr(case_type, resolve=False).default_setting()
        return _conf.guild(guild).casetypes.get_attr(case_type, default)
    else:
        raise RuntimeError("That case type is not registered!")


def get_case_type_repr(case_type: str) -> str:
    """
    Gets the string representation of a case type
    :param str case_type: the case type to get the representation of
    :return: The case type's representation
    """
    return _conf.casetypes.get_attr(case_type, resolve=False).image()


async def reset_cases(guild: discord.Guild) -> bool:
    """
    Wipes all modlog cases for the specified guild
    :param discord.Guild guild: the guild to reset cases for
    :return: True if successful
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
