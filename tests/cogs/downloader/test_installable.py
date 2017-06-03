import pytest
import json

from cogs.downloader.installable import Installable, InstallableType
from pathlib import Path

INFO_JSON = {
    "author": (
        "tekulvw",
    ),
    "bot_version": (3, 0, 0),
    "description": "A long description",
    "hidden": False,
    "install_msg": "A post-installation message",
    "required_cogs": {},
    "requirements": (
        "tabulate"
    ),
    "short": "A short description",
    "tags": (
        "tag1",
        "tag2"
    ),
    "type": "COG"
}


def test_process_info_file(tmpdir):
    info_path = tmpdir.join("info.json")
    info_path.write_text(json.dumps(INFO_JSON), 'utf-8')

    cog_info = Installable(Path(str(tmpdir)))

    for k, v in INFO_JSON.items():
        if k == "type":
            assert cog_info.type == InstallableType.COG
        else:
            assert getattr(cog_info, k) == v
