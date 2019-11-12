# -*- coding: utf-8 -*-
# Red Dependencies
import pytest

# Red Imports
from redbot.pytest.alias import *


def test_is_valid_alias_name(alias):
    assert alias.is_valid_alias_name("valid") is True
    assert alias.is_valid_alias_name("not valid name") is False


@pytest.mark.asyncio
async def test_empty_guild_aliases(alias, empty_guild):
    assert list(await alias.unloaded_aliases(empty_guild)) == []


@pytest.mark.asyncio
async def test_empty_global_aliases(alias):
    assert list(await alias.unloaded_global_aliases()) == []


async def create_test_guild_alias(alias, ctx):
    await alias.add_alias(ctx, "test", "ping", global_=False)


async def create_test_global_alias(alias, ctx):
    await alias.add_alias(ctx, "test", "ping", global_=True)


@pytest.mark.asyncio
async def test_add_guild_alias(alias, ctx):
    await create_test_guild_alias(alias, ctx)

    is_alias, alias_obj = await alias.is_alias(ctx.guild, "test")
    assert is_alias is True
    assert alias_obj.global_ is False


@pytest.mark.asyncio
async def test_delete_guild_alias(alias, ctx):
    await create_test_guild_alias(alias, ctx)
    is_alias, _ = await alias.is_alias(ctx.guild, "test")
    assert is_alias is True

    await alias.delete_alias(ctx, "test")

    is_alias, _ = await alias.is_alias(ctx.guild, "test")
    assert is_alias is False


@pytest.mark.asyncio
async def test_add_global_alias(alias, ctx):
    await create_test_global_alias(alias, ctx)
    is_alias, alias_obj = await alias.is_alias(ctx.guild, "test")

    assert is_alias is True
    assert alias_obj.global_ is True


@pytest.mark.asyncio
async def test_delete_global_alias(alias, ctx):
    await create_test_global_alias(alias, ctx)
    is_alias, alias_obj = await alias.is_alias(ctx.guild, "test")
    assert is_alias is True
    assert alias_obj.global_ is True

    did_delete = await alias.delete_alias(ctx, alias_name="test", global_=True)
    assert did_delete is True
