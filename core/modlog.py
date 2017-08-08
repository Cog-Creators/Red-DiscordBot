import discord
from core import Config
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

Case = namedtuple(
    "Case",
    "guild case_number action_type created_at modified_at channel "
    "reason until user moderator amended_by"
)

_conf = Config.get_conf(_modlog_type(), 1354799444)


def _register_defaults():
    _conf.register_global(**_DEFAULT_GLOBAL)
    _conf.register_guild(**_DEFAULT_GUILD)


_register_defaults()


def get_case(case_number: int) -> Case:
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
                      ) -> Case:
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
    :return: the created case
    :rtype: Case
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
        "channel": channel.id if hasattr(channel, "id") else None
    }

    try:
        mod_channel = get_modlog_channel(guild)
    except RuntimeError:
        raise
    if not is_casetype(action_type):
        raise RuntimeError("That action type is not registered!")



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
        return _conf.guild(guild).casetypes.get_attr(
            case_type, _conf.casetypes.get_attr(case_type)
        )
    else:
        raise RuntimeError("That case type is not registered!")


async def reset_cases(guild: discord.Guild) -> bool:
    """
    Wipes all modlog cases for the specified guild
    :param discord.Guild guild: the guild to reset cases for
    :return: True if successful
    """
    await _conf.guild(guild).cases.set({})
    return True
