import pytest


@pytest.fixture
def mod(config):
    from core import Config

    Config.get_conf = lambda *args, **kwargs: config

    from core import modlog

    modlog._register_defaults()
    return modlog


@pytest.mark.asyncio
async def test_modlog_register_casetype(mod, ctx):
    await mod.register_casetype(
        {
            "name": "ban",
            "default_setting": True,
            "image": "https://twemoji.maxcdn.com/2/72x72/1f528.png",
            "case_str": "Ban"
        }
    )
    assert await mod.is_casetype("ban") is True


@pytest.mark.asyncio
async def test_modlog_case_create(mod, ctx, member_factory):
    from datetime import datetime as dt
    usr = member_factory.get()
    guild = ctx.guild
    case_type = "ban"
    moderator = ctx.author
    reason = "Test 12345"
    created_at = dt.utcnow()
    case = await mod.create_case(
        guild, created_at, case_type, usr, moderator, reason
    )
    assert case.user == usr
    assert case.action_type == case_type
    assert case.moderator == moderator
    assert case.reason == reason
    assert case.created_at == created_at.timestamp()


@pytest.mark.asyncio
async def test_modlog_set_modlog_channel(mod, ctx):
    await mod.set_modlog_channel(ctx.channel)
    assert mod.get_modlog_channel == ctx.channel
