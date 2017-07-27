import datetime
from collections import namedtuple
from typing import Tuple, Generator, Union

import discord

from core import Config

__all__ = ["get_balance", "set_balance", "withdraw_credits", "deposit_credits",
           "can_spend", "transfer_credits", "wipe_bank", "get_guild_accounts",
           "get_global_accounts", "get_account"]

DEFAULT_GLOBAL = {
    "is_global": False,
    "bank_name": "Twentysix bank",
    "currency": "credits"
}

DEFAULT_GUILD = {
    "bank_name": "Twentysix bank",
    "currency": "credits"
}

DEFAULT_MEMBER = {
    "name": "",
    "balance": 0,
    "created_at": ""
}

DEFAULT_USER = DEFAULT_MEMBER

bank_type = type("Bank")
Account = namedtuple("Account", "name", "balance", "created_at")

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
    return int(time.timestamp())


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
    if conf.is_global():
        return conf.user(member).balance()
    return conf.member(member).balance()


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
    if conf.is_global():
        group = conf.user(member)
    else:
        group = conf.member(member)
    await group.balance.set(amount)

    if group.created_at() == "":
        await group.created_at.set(encoded_current_time())

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
    if conf.is_global():
        await conf.user(user).clear()
    else:
        await conf.member(user).clear()


def get_guild_accounts(guild: discord.Guild) -> Generator[Account]:
    """
    Gets all account data for the given guild.

    May raise RuntimeError if the bank is currently global.
    :param guild:
    :return:
    """
    if conf.is_global():
        raise RuntimeError("The bank is currently global.")

    accs = conf.member(guild.owner).all()
    for acc in accs:
        acc['created_at'] = decode_time(acc['created_at'])
        yield Account(**acc)


def get_global_accounts(guild: discord.Guild) -> Generator[Account]:
    """
    Gets all global account data.

    May raise RuntimeError if the bank is currently guild specific.
    :param guild:
    :return:
    """
    if not conf.is_global():
        raise RuntimeError("The bank is not currently global.")

    accs = conf.user(guild.owner).all()
    for acc in accs:
        acc['created_at'] = decode_time(acc['created_at'])
        yield Account(**acc)


def get_account(member: Union[discord.Member, discord.User]) -> Account:
    """
    Gets the appropriate account for the given member.
    :param member:
    :return:
    """
    if conf.is_global():
        acc_data = conf.user(member)()
    else:
        acc_data = conf.member(member)()

    acc_data['created_at'] = decode_time(acc_data['created_at'])

    return Account(**acc_data)
