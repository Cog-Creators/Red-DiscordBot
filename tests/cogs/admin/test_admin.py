from unittest.mock import MagicMock

import pytest

from redbot.cogs.admin import Admin
from redbot.cogs.admin.announcer import Announcer


@pytest.fixture()
def admin(config):
    return Admin(config)


@pytest.fixture()
def announcer(admin):
    a = Announcer(MagicMock(), "Some message", admin.conf)
    yield a
    a.cancel()


@pytest.mark.asyncio
async def test_serverlock_check(admin, coroutine):
    await admin.conf.serverlocked.set(True)
    guild = MagicMock()
    guild.leave = coroutine

    # noinspection PyProtectedMember
    ret = await admin._serverlock_check(guild)

    assert ret is True


def test_announcer_initial_state(announcer):
    assert announcer.active is None


def test_announcer_start(announcer):
    announcer.announcer = object
    announcer.start()

    assert announcer.ctx.bot.loop.create_task.called
    assert announcer.active is True


@pytest.mark.asyncio
async def test_announcer_ignore(announcer, empty_guild, empty_channel):
    await announcer.config.guild(empty_guild).announce_channel.set(empty_channel.id)

    guild = MagicMock()
    guild.id = empty_guild.id

    guild.get_channel.return_value = empty_channel

    ret = announcer._get_announce_channel(guild)

    assert guild.get_channel.called
    assert ret == empty_channel
