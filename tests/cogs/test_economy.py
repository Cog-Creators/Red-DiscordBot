import pytest


@pytest.fixture()
def bank(config):
    from redbot.core import Config

    Config.get_conf = lambda *args, **kwargs: config

    from redbot.core import bank

    bank._register_defaults()
    return bank


@pytest.mark.asyncio
async def test_bank_register(bank, ctx):
    default_bal = await bank.get_default_balance(ctx.guild)
    assert default_bal == (await bank.get_account(ctx.author)).balance


async def has_account(member, bank):
    balance = await bank.get_balance(member)
    if balance == 0:
        balance = 1
    await bank.set_balance(member, balance)


@pytest.mark.asyncio
async def test_bank_transfer(bank, member_factory):
    mbr1 = member_factory.get()
    mbr2 = member_factory.get()
    bal1 = (await bank.get_account(mbr1)).balance
    bal2 = (await bank.get_account(mbr2)).balance
    await bank.transfer_credits(mbr1, mbr2, 50)
    newbal1 = (await bank.get_account(mbr1)).balance
    newbal2 = (await bank.get_account(mbr2)).balance
    assert bal1 - 50 == newbal1
    assert bal2 + 50 == newbal2


@pytest.mark.asyncio
async def test_bank_set(bank, member_factory):
    mbr = member_factory.get()
    await bank.set_balance(mbr, 250)
    acc = await bank.get_account(mbr)
    assert acc.balance == 250


@pytest.mark.asyncio
async def test_bank_can_spend(bank, member_factory):
    mbr = member_factory.get()
    canspend = await bank.can_spend(mbr, 50)
    assert canspend == (50 < await bank.get_default_balance(mbr.guild))
    await bank.set_balance(mbr, 200)
    acc = await bank.get_account(mbr)
    canspendnow = await bank.can_spend(mbr, 100)
    assert canspendnow
