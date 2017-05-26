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
