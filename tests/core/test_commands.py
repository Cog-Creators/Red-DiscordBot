import inspect
import datetime
from unittest.mock import AsyncMock, MagicMock
from dateutil.relativedelta import relativedelta

import pytest
from discord.ext import commands as dpy_commands

from redbot.core import commands
from redbot.core.commands import converter
from redbot.core.commands.requires import PermState


@pytest.fixture(scope="session")
def group():
    @commands.group()
    async def fixturegroup(*args, **kwargs):
        return args, kwargs

    return fixturegroup


def is_Command(obj):
    return isinstance(obj, commands.Command)


def is_Group(obj):
    return isinstance(obj, commands.Group)


def test_command_decorators(coroutine):
    assert is_Command(commands.command(name="cmd")(coroutine))
    assert is_Group(commands.group(name="grp")(coroutine))


def test_group_decorator_methods(group, coroutine):
    assert is_Command(group.command(name="cmd")(coroutine))
    assert is_Group(group.group(name="grp")(coroutine))


def test_bot_decorator_methods(red, coroutine):
    assert is_Command(red.command(name="cmd")(coroutine))
    assert is_Group(red.group(name="grp")(coroutine))


def test_dpy_commands_reexports():
    dpy_attrs = set()
    for attr_name, attr_value in dpy_commands.__dict__.items():
        if attr_name.startswith("_") or inspect.ismodule(attr_value):
            continue

        dpy_attrs.add(attr_name)

    missing_attrs = dpy_attrs - set(commands.__dict__.keys())

    if missing_attrs:
        pytest.fail(
            "redbot.core.commands is missing these names from discord.ext.commands: "
            + ", ".join(missing_attrs)
        )


def test_converter_timedelta():
    assert converter.parse_timedelta("1 day") == datetime.timedelta(days=1)
    assert converter.parse_timedelta("1 minute") == datetime.timedelta(minutes=1)
    assert converter.parse_timedelta("13 days 5 minutes") == datetime.timedelta(days=13, minutes=5)


def test_converter_relativedelta():
    assert converter.parse_relativedelta("1 year") == relativedelta(years=1)
    assert converter.parse_relativedelta("1 year 10 days 3 seconds") == relativedelta(
        years=1, days=10, seconds=3
    )


def _ctx_invoking(command):
    ctx = MagicMock()
    ctx.bot.can_run = AsyncMock(return_value=True)
    ctx.command = command
    ctx.permission_state = PermState.NORMAL
    return ctx


async def test_can_run_restores_context_when_parent_refuses(monkeypatch):
    @commands.command()
    async def invoked(ctx):
        pass

    @commands.group()
    async def locked(ctx):
        pass

    @locked.command()
    async def sub(ctx):
        pass

    monkeypatch.setattr(locked.requires, "verify", AsyncMock(return_value=False))
    ctx = _ctx_invoking(invoked)

    assert await sub.can_run(ctx, check_all_parents=True) is False
    assert ctx.command is invoked
    assert ctx.permission_state is PermState.NORMAL


async def test_can_run_restores_context_when_cog_refuses(monkeypatch):
    @commands.command()
    async def invoked(ctx):
        pass

    class Locked(commands.Cog):
        @commands.command()
        async def top(self, ctx):
            pass

    cog = Locked()
    # Set by `bot.add_cog()` in a running bot.
    cog.top.cog = cog
    monkeypatch.setattr(cog.requires, "verify", AsyncMock(return_value=False))
    ctx = _ctx_invoking(invoked)

    assert await cog.top.can_run(ctx) is False
    assert ctx.command is invoked
    assert ctx.permission_state is PermState.NORMAL
