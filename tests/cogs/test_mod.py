import pytest


@pytest.fixture
def mod(config):
    from redbot.core import Config

    Config.get_conf = lambda *args, **kwargs: config

    from redbot.core import modlog

    modlog._register_defaults()
    return modlog


@pytest.mark.asyncio
async def test_modlog_register_casetype(mod, ctx):
    ct = {
        "name": "ban",
        "default_setting": True,
        "image": ":hammer:",
        "case_str": "Ban",
        "audit_type": "ban",
    }
    casetype = await mod.register_casetype(**ct)
    assert casetype is not None


@pytest.mark.asyncio
async def test_modlog_case_create(mod, ctx, member_factory):
    from datetime import datetime as dt

    usr = member_factory.get()
    guild = ctx.guild
    bot = ctx.bot
    case_type = "ban"
    moderator = ctx.author
    reason = "Test 12345"
    created_at = dt.utcnow()
    case = await mod.create_case(bot, guild, created_at, case_type, usr, moderator, reason)
    assert case is not None
    assert case.user == usr
    assert case.action_type == case_type
    assert case.moderator == moderator
    assert case.reason == reason
    assert case.created_at == int(created_at.timestamp())


@pytest.mark.asyncio
async def test_modlog_set_modlog_channel(mod, ctx):
    await mod.set_modlog_channel(ctx.guild, ctx.channel)
    assert await mod.get_modlog_channel(ctx.guild) == ctx.channel.id
