import inspect
import datetime
from types import SimpleNamespace
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


@pytest.fixture()
def refusing_ctx():
    async def can_run(ctx):
        return True

    return SimpleNamespace(
        bot=SimpleNamespace(can_run=can_run),
        command="original",
        permission_state=PermState.ACTIVE_ALLOW,
    )


async def _refuse(self, ctx):
    ctx.permission_state = PermState.CAUTIOUS_ALLOW
    return False


async def test_can_run_restores_ctx_when_parent_refuses(monkeypatch, refusing_ctx):
    @commands.group()
    async def parent(ctx):
        pass

    @parent.command()
    async def child(ctx):
        pass

    monkeypatch.setattr(type(parent.requires), "verify", _refuse)

    assert await child.can_run(refusing_ctx, check_all_parents=True) is False
    assert refusing_ctx.command == "original"
    assert refusing_ctx.permission_state is PermState.ACTIVE_ALLOW


async def test_can_run_restores_ctx_when_cog_refuses(monkeypatch, refusing_ctx):
    class SomeCog(commands.Cog):
        @commands.command()
        async def cmd(self, ctx):
            pass

    cog = SomeCog()
    cog.cmd.cog = cog
    monkeypatch.setattr(type(cog.requires), "verify", _refuse)

    assert await cog.cmd.can_run(refusing_ctx) is False
    assert refusing_ctx.command == "original"
    assert refusing_ctx.permission_state is PermState.ACTIVE_ALLOW
