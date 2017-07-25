import pytest

from cogs.bank import bank


@pytest.fixture(scope='module')
def banks(monkeysession, config):
    def get_mock_conf(*args, **kwargs):
        return config

    monkeysession.setattr("core.config.Config.get_conf", get_mock_conf)

    return bank


@pytest.mark.asyncio
async def test_bank_register(banks, ctx):
    acc = await banks.create_account(ctx.author, initial_balance=0)
    assert isinstance(acc, dict)
    assert acc["balance"] == 0


@pytest.mark.asyncio
async def test_bank_transfer(banks, random_member):
    mbr1 = random_member.get()
    mbr2 = random_member.get()
    acc1 = await bank.create_account(mbr1, initial_balance=100)
    acc2 = await bank.create_account(mbr2)
    transfer_success = await bank.transfer_credits(mbr1, mbr2, 50)
    assert transfer_success
    acc1 = bank.get_account(mbr1)
    acc2 = bank.get_account(mbr2)
    assert acc1["balance"] == 50
    assert acc2["balance"] == 50


@pytest.mark.asyncio
async def test_bank_set(banks, random_member):
    mbr = random_member.get()
    acc = await bank.create_account(mbr)
    set_success = await bank.set_credits(mbr, 250)
    assert set_success
    acc = bank.get_account(mbr)
    assert acc["balance"] == 250


@pytest.mark.asyncio
async def test_bank_can_spend(banks, random_member):
    mbr = random_member.get()
    acc = await bank.create_account(mbr)
    canspend = bank.can_spend(mbr, 50)
    assert not canspend
    await bank.set_credits(mbr, 200)
    acc = bank.get_account(mbr)
    canspendnow = bank.can_spend(mbr, 100)
    assert canspendnow


@pytest.mark.asyncio
async def test_bank_get_balance(banks, random_member):
    mbr = random_member.get()
    await bank.create_account(mbr)
    cur_balance = bank.get_balance(mbr)
    assert cur_balance == 0
