import pytest
from collections import namedtuple

from redbot.pytest.dataconverter import *
from redbot.core.utils.data_converter import DataConverter


def mock_dpy_object(id_):
    return namedtuple("DPYObject", "id")(int(id_))


def mock_dpy_member(guildid, userid):
    return namedtuple("Member", "id guild")(int(userid), mock_dpy_object(guildid))


@pytest.mark.asyncio
async def test_mod_nicknames(red):
    specresolver = get_specresolver(__file__)
    filepath, converter, cogname, attr, _id = specresolver.get_conversion_info("Past Nicknames")
    conf = specresolver.get_config_object(red, cogname, attr, _id)

    v2data = DataConverter.json_load(filepath)

    await specresolver.convert(red, "Past Nicknames", config=conf)

    for guildid, guild_data in v2data.items():
        guild = mock_dpy_object(guildid)
        for userid, user_data in guild_data.items():
            member = mock_dpy_member(guildid, userid)

            assert await conf.member(member).past_nicks() == user_data
