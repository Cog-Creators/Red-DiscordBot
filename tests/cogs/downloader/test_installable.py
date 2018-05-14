import json
from pathlib import Path

import pytest

from redbot.cogs.downloader.installable import Installable, InstallableType

INFO_JSON = {
    "author": ("tekulvw",),
    "bot_version": (3, 0, 0),
    "description": "A long description",
    "hidden": False,
    "install_msg": "A post-installation message",
    "required_cogs": {},
    "requirements": ("tabulate"),
    "short": "A short description",
    "tags": ("tag1", "tag2"),
    "type": "COG",
}


@pytest.fixture
def installable(tmpdir):
    cog_path = tmpdir.mkdir("test_repo").mkdir("test_cog")
    info_path = cog_path.join("info.json")
    info_path.write_text(json.dumps(INFO_JSON), "utf-8")

    cog_info = Installable(Path(str(cog_path)))
    return cog_info


def test_process_info_file(installable):
    for k, v in INFO_JSON.items():
        if k == "type":
            assert installable.type == InstallableType.COG
        else:
            assert getattr(installable, k) == v


# noinspection PyProtectedMember
def test_location_is_dir(installable):
    assert installable._location.exists()
    assert installable._location.is_dir()


# noinspection PyProtectedMember
def test_info_file_is_file(installable):
    assert installable._info_file.exists()
    assert installable._info_file.is_file()


def test_name(installable):
    assert installable.name == "test_cog"


def test_repo_name(installable):
    assert installable.repo_name == "test_repo"


def test_serialization(installable):
    data = installable.to_json()
    cog_name = data["cog_name"]

    assert cog_name == "test_cog"
