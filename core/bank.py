import datetime
from collections import namedtuple
from typing import Tuple, Generator, Union

import discord
from copy import deepcopy

from core import Config

__all__ = ["get_balance", "set_balance", "withdraw_credits", "deposit_credits",
           "can_spend", "transfer_credits", "wipe_bank", "get_guild_accounts",
           "get_global_accounts", "get_account", "is_global", "get_bank_name",
           "set_bank_name", "get_currency_name", "set_currency_name",
           "get_default_balance", "set_default_balance"]

DEFAULT_GLOBAL = {
    "is_global": False,
    "bank_name": "Twentysix bank",
    "currency": "credits",
    "default_balance": 100
}

DEFAULT_GUILD = {
    "bank_name": "Twentysix bank",
    "currency": "credits",
    "default_balance": 100
}

DEFAULT_MEMBER = {
    "name": "",
    "balance": 0,
    "created_at": 0
}

DEFAULT_USER = DEFAULT_MEMBER

bank_type = type("Bank")
Account = namedtuple("Account", "name balance created_at")

conf = Config.get_conf(bank_type(), 384734293238749, force_registration=True)
conf.register_global(**DEFAULT_GLOBAL)
conf.register_guild(**DEFAULT_GUILD)
conf.register_member(**DEFAULT_MEMBER)
conf.register_user(**DEFAULT_USER)


def encoded_current_time() -> int:
    """
    Encoded current timestamp in UTC.
    :return:
    """
    now = datetime.datetime.utcnow()
    return encode_time(now)


def encode_time(time: datetime.datetime) -> int:
    """
    Goes from datetime object to serializable int.
    :param time:
    :return:
    """
    ret = int(time.timestamp())
    return ret


def decode_time(time: int) -> datetime.datetime:
    """
    Returns decoded timestamp in UTC.
    :param time:
    :return:
    """
    return datetime.datetime.utcfromtimestamp(time)


def get_balance(member: discord.Member) -> int:
    """
    Gets the current balance of a member.
    :param member:
    :return:
    """
    acc = get_account(member)
    return acc.balance


def can_spend(member: discord.Member, amount: int) -> bool:
    """
    Determines if a member can spend the given amount.
    :param member:
    :param amount:
    :return:
    """
    if _invalid_depwith_amount(amount):
        return False
    return get_balance(member) > amount


async def set_balance(member: discord.Member, amount: int) -> int:
    """
    Sets an account balance.

    May raise ValueError if amount is invalid.
    :param member:
    :param amount:
    :return: New account balance.
    """
    if amount < 0:
        raise ValueError("Not allowed to have negative balance.")
    if is_global():
        group = conf.user(member)
    else:
        group = conf.member(member)
    await group.balance.set(amount)

    if group.created_at() == 0:
        time = encoded_current_time()
        await group.created_at.set(time)

    if group.name() == "":
        await group.name.set(member.display_name)

    return amount


def _invalid_depwith_amount(amount: int) -> bool:
    return amount <= 0


async def withdraw_credits(member: discord.Member, amount: int) -> int:
    """
    Removes a certain amount of credits from an account.

    May raise ValueError if the amount is invalid or if the account has
        insufficient funds.
    :param member:
    :param amount:
    :return: New account balance.
    """
    if _invalid_depwith_amount(amount):
        raise ValueError("Invalid withdrawal amount {} <= 0".format(amount))

    bal = get_balance(member)
    if amount > bal:
        raise ValueError("Insufficient funds {} > {}".format(amount, bal))

    return await set_balance(member, bal - amount)


async def deposit_credits(member: discord.Member, amount: int) -> int:
    """
    Adds a given amount of credits to an account.

    May raise ValueError if the amount is invalid.
    :param member:
    :param amount:
    :return:
    """
    if _invalid_depwith_amount(amount):
        raise ValueError("Invalid withdrawal amount {} <= 0".format(amount))

    bal = get_balance(member)
    return await set_balance(member, amount + bal)


async def transfer_credits(from_: discord.Member, to: discord.Member, amount: int):
    """
    Transfers a given amount of credits from one account to another.

    May raise ValueError if the amount is invalid or if the from_
        account has insufficient funds.
    :param from_:
    :param to:
    :param amount:
    :return:
    """
    if _invalid_depwith_amount(amount):
        raise ValueError("Invalid transfer amount {} <= 0".format(amount))

    await withdraw_credits(from_, amount)
    return await deposit_credits(to, amount)


async def wipe_bank(guild: discord.Guild):
    """
    Deletes all accounts from the bank.
    :return:
    """
    user = guild.owner
    if is_global():
        await conf.user(user).clear()
    else:
        await conf.member(user).clear()


def get_guild_accounts(guild: discord.Guild) -> Generator[Account, None, None]:
    """
    Gets all account data for the given guild.

    May raise RuntimeError if the bank is currently global.
    :param guild:
    :return:
    """
    if is_global():
        raise RuntimeError("The bank is currently global.")

    accs = conf.member(guild.owner).all()
    for acc in accs:
        acc['created_at'] = decode_time(acc['created_at'])
        yield Account(**acc)


def get_global_accounts(user: discord.User) -> Generator[Account, None, None]:
    """
    Gets all global account data.

    May raise RuntimeError if the bank is currently guild specific.
    :param guild:
    :return:
    """
    if not is_global():
        raise RuntimeError("The bank is not currently global.")

    accs = conf.user(user).all()
    for acc in accs:
        acc['created_at'] = decode_time(acc['created_at'])
        yield Account(**acc)


def get_account(member: Union[discord.Member, discord.User]) -> Account:
    """
    Gets the appropriate account for the given member.
    :param member:
    :return:
    """
    if is_global():
        acc_data = deepcopy(conf.user(member)())
        default = deepcopy(DEFAULT_USER)
    else:
        acc_data = deepcopy(conf.member(member)())
        default = deepcopy(DEFAULT_MEMBER)

    if acc_data == {}:
        acc_data = default
        acc_data['name'] = member.display_name
        try:
            acc_data['balance'] = get_default_balance(member.guild)
        except AttributeError:
            acc_data['balance'] = get_default_balance()

    acc_data['created_at'] = decode_time(acc_data['created_at'])
    return Account(**acc_data)


def is_global() -> bool:
    """
    Determines if the bank is currently global.
    :return:
    """
    return conf.is_global()


async def set_global(global_: bool, user: Union[discord.User, discord.Member]) -> bool:
    """
    Sets global status of the bank, all accounts are reset when you switch!
    :param global_: True will set bank to global mode.
    :param user: Must be a Member object if changing TO global mode.
    :return: New bank mode, True is global.
    """
    if is_global() is global_:
        return global_

    if is_global():
        await conf.user(user).clear()
    elif isinstance(user, discord.Member):
        await conf.member(user).clear_all()
    else:
        raise RuntimeError("You must provide a member if you're changing to global"
                           " bank mode.")

    await conf.is_global.set(global_)
    return global_


def get_bank_name(guild: discord.Guild=None) -> str:
    """
    Gets the current bank name. If the bank is guild-specific the
        guild parameter is required.

    May raise RuntimeError if guild is missing and required.
    :param guild:
    :return:
    """
    if is_global():
        return conf.bank_name()
    elif guild is not None:
        return conf.guild(guild).bank_name()
    else:
        raise RuntimeError("Guild parameter is required and missing.")


async def set_bank_name(name: str, guild: discord.Guild=None) -> str:
    """
    Sets the bank name, if bank is server specific the guild parameter is
        required.

    May throw RuntimeError if guild is required and missing.
    :param name:
    :param guild:
    :return:
    """
    if is_global():
        await conf.bank_name.set(name)
    elif guild is not None:
        await conf.guild(guild).bank_name.set(name)
    else:
        raise RuntimeError("Guild must be provided if setting the name of a guild"
                           "-specific bank.")
    return name


def get_currency_name(guild: discord.Guild=None) -> str:
    """
    Gets the currency name of the bank. The guild parameter is required if
        the bank is guild-specific.

    May raise RuntimeError if the guild is missing and required.
    :param guild:
    :return:
    """
    if is_global():
        return conf.currency()
    elif guild is not None:
        return conf.guild(guild).currency()
    else:
        raise RuntimeError("Guild must be provided.")


async def set_currency_name(name: str, guild: discord.Guild=None) -> str:
    """
    Sets the currency name for the bank, if bank is guild specific the
        guild parameter is required.

    May raise RuntimeError if guild is missing and required.
    :param name:
    :param guild:
    :return:
    """
    if is_global():
        await conf.currency.set(name)
    elif guild is not None:
        await conf.guild(guild).currency.set(name)
    else:
        raise RuntimeError("Guild must be provided if setting the currency"
                           " name of a guild-specific bank.")
    return name


def get_default_balance(guild: discord.Guild=None) -> int:
    """
    Gets the current default balance amount. If the bank is guild-specific
        you must pass guild.

    May raise RuntimeError if guild is missing and required.
    :param guild:
    :return:
    """
    if is_global():
        return conf.default_balance()
    elif guild is not None:
        return conf.guild(guild).default_balance()
    else:
        raise RuntimeError("Guild is missing and required!")


async def set_default_balance(amount: int, guild: discord.Guild=None) -> int:
    """
    Sets the default balance amount. Guild is required if the bank is
        guild-specific.

    May raise RuntimeError if guild is missing and required.
    May raise ValueError if amount is invalid.
    :param guild:
    :param amount:
    :return:
    """
    amount = int(amount)
    if amount < 0:
        raise ValueError("Amount must be greater than zero.")

    if is_global():
        await conf.default_balance.set(amount)
    elif guild is not None:
        await conf.guild(guild).default_balance.set(amount)
    else:
        raise RuntimeError("Guild is missing and required.")
