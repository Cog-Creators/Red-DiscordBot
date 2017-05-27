from collections import namedtuple
from pathlib import Path

import pytest
import random

from core.bot import Red
from core.drivers import red_json
from core import Config


@pytest.fixture(scope="module")
def json_driver(tmpdir_factory):
    driver = red_json.JSON(
        "PyTest",
        data_path_override=Path(str(tmpdir_factory.getbasetemp()))
    )
    return driver


@pytest.fixture(scope="module")
def config(json_driver):
    return Config(
        cog_name="PyTest",
        unique_identifier=0,
        driver_spawn=json_driver)


@pytest.fixture(scope="module")
def config_fr(json_driver):
    """
    Mocked config object with force_register enabled.
    """
    return Config(
        cog_name="PyTest",
        unique_identifier=0,
        driver_spawn=json_driver,
        force_registration=True
    )


#region Dpy Mocks
@pytest.fixture(scope="module")
def empty_guild():
    mock_guild = namedtuple("Guild", "id members")
    return mock_guild(random.randint(1, 999999999), [])


@pytest.fixture(scope="module")
def empty_channel():
    mock_channel = namedtuple("Channel", "id")
    return mock_channel(random.randint(1, 999999999))


@pytest.fixture(scope="module")
def empty_role():
    mock_role = namedtuple("Role", "id")
    return mock_role(random.randint(1, 999999999))


@pytest.fixture(scope="module")
def empty_member(empty_guild):
    mock_member = namedtuple("Member", "id guild")
    return mock_member(random.randint(1, 999999999), empty_guild)


@pytest.fixture(scope="module")
def empty_user():
    mock_user = namedtuple("User", "id")
    return mock_user(random.randint(1, 999999999))


@pytest.fixture(scope="module")
def empty_message():
    mock_msg = namedtuple("Message", "content")
    return mock_msg("No content.")


@pytest.fixture(scope="module")
def ctx(empty_member, empty_channel, red):
    mock_ctx = namedtuple("Context", "author guild channel message bot")
    return mock_ctx(empty_member, empty_member.guild, empty_channel,
                    empty_message, red)
#endregion


#region Red Mock
@pytest.fixture
def red(monkeypatch, config_fr, event_loop):
    from core.settings import parse_cli_flags
    cli_flags = parse_cli_flags()

    description = "Red v3 - Alpha"

    monkeypatch.setattr("core.config.Config.get_core_conf",
                        lambda *args, **kwargs: config_fr)

    red = Red(cli_flags, description=description, pm_help=None,
              loop=event_loop)
    return red
#endregion