from collections import namedtuple

import pytest
import random

from core.drivers import red_json
from core import Config


@pytest.fixture(scope="module")
def json_driver(tmpdir_factory):
    driver = red_json.JSON(
        "PyTest",
        data_path_override=tmpdir_factory.getbasetemp()
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
@pytest.fixture
def empty_guild():
    mock_guild = namedtuple("Guild", "id members")
    return mock_guild(random.randint(1, 999999999), [])


@pytest.fixture
def empty_channel():
    mock_channel = namedtuple("Channel", "id")
    return mock_channel(random.randint(1, 999999999))


@pytest.fixture
def empty_role():
    mock_role = namedtuple("Role", "id")
    return mock_role(random.randint(1, 999999999))


@pytest.fixture
def empty_member(empty_guild):
    mock_member = namedtuple("Member", "id guild")
    return mock_member(random.randint(1, 999999999), empty_guild)


@pytest.fixture
def empty_user():
    mock_user = namedtuple("User", "id")
    return mock_user(random.randint(1, 999999999))
#endregion
