from cogs.alias import Alias
import pytest


@pytest.fixture(scope="module")
def alias(monkeysession, config):
    def get_mock_conf(*args, **kwargs):
        return config

    monkeysession.setattr("core.config.Config.get_conf", get_mock_conf)

    return Alias(None)


def test_is_valid_alias_name(alias):
    assert alias.is_valid_alias_name("valid") is True
    assert alias.is_valid_alias_name("not valid name") is False


def test_empty_guild_aliases(alias, empty_guild):
    assert list(alias.unloaded_aliases(empty_guild)) == []


def test_empty_global_aliases(alias):
    assert list(alias.unloaded_global_aliases()) == []


@pytest.mark.asyncio
async def test_add_guild_alias(alias, ctx):
    await alias.add_alias(ctx, "test", "ping", global_=False)

    is_alias, alias_obj = alias.is_alias(ctx.guild, "test")
    assert is_alias is True
    assert alias_obj.global_ is False


@pytest.mark.asyncio
async def test_delete_guild_alias(alias, ctx):
    is_alias, _ = alias.is_alias(ctx.guild, "test")
    assert is_alias is True

    await alias.delete_alias(ctx, "test")

    is_alias, _ = alias.is_alias(ctx.guild, "test")
    assert is_alias is False


@pytest.mark.asyncio
async def test_add_global_alias(alias, ctx):
    await alias.add_alias(ctx, "test", "ping", global_=True)
    is_alias, alias_obj = alias.is_alias(ctx.guild, "test")

    assert is_alias is True
    assert alias_obj.global_ is True


@pytest.mark.asyncio
async def test_delete_global_alias(alias, ctx):
    is_alias, alias_obj = alias.is_alias(ctx.guild, "test")
    assert is_alias is True
    assert alias_obj.global_ is True

    did_delete = await alias.delete_alias(ctx, alias_name="test", global_=True)
    assert did_delete is True
