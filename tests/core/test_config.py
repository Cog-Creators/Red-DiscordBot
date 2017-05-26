import pytest


#region Register Tests
def test_config_register_global(config):
    config.register_global(enabled=False)
    assert config.defaults["GLOBAL"]["enabled"] is False
    assert config.enabled() is False


def test_config_register_guild(config, empty_guild):
    config.register_guild(enabled=False, some_list=[], some_dict={})
    assert config.defaults["GUILD"]["enabled"] is False
    assert config.defaults["GUILD"]["some_list"] == []
    assert config.defaults["GUILD"]["some_dict"] == {}

    assert config.guild(empty_guild).enabled() is False
    assert config.guild(empty_guild).some_list() == []
    assert config.guild(empty_guild).some_dict() == {}


def test_config_register_channel(config, empty_channel):
    config.register_channel(enabled=False)
    assert config.defaults["CHANNEL"]["enabled"] is False
    assert config.channel(empty_channel).enabled() is False


def test_config_register_role(config, empty_role):
    config.register_role(enabled=False)
    assert config.defaults["ROLE"]["enabled"] is False
    assert config.role(empty_role).enabled() is False


def test_config_register_member(config, empty_member):
    config.register_member(some_number=-1)
    assert config.defaults["MEMBER"]["some_number"] == -1
    assert config.member(empty_member).some_number() == -1


def test_config_register_user(config, empty_user):
    config.register_user(some_value=None)
    assert config.defaults["USER"]["some_value"] is None
    assert config.user(empty_user).some_value() is None


def test_config_force_register_global(config_fr):
    with pytest.raises(AttributeError):
        config_fr.enabled()

    config_fr.register_global(enabled=True)
    assert config_fr.enabled() is True
#endregion


#region Default Value Overrides
def test_global_default_override(config):
    assert config.enabled(True) is True
    assert config.get("enabled") is None
    assert config.get("enabled", default=True) is True


def test_global_default_nofr(config):
    assert config.nofr() is None
    assert config.nofr(True) is True
    assert config.get("nofr") is None
    assert config.get("nofr", default=True) is True


def test_guild_default_override(config, empty_guild):
    assert config.guild(empty_guild).enabled(True) is True
    assert config.guild(empty_guild).get("enabled") is None
    assert config.guild(empty_guild).get("enabled", default=True) is True


def test_channel_default_override(config, empty_channel):
    assert config.channel(empty_channel).enabled(True) is True
    assert config.channel(empty_channel).get("enabled") is None
    assert config.channel(empty_channel).get("enabled", default=True) is True


def test_role_default_override(config, empty_role):
    assert config.role(empty_role).enabled(True) is True
    assert config.role(empty_role).get("enabled") is None
    assert config.role(empty_role).get("enabled", default=True) is True


def test_member_default_override(config, empty_member):
    assert config.member(empty_member).enabled(True) is True
    assert config.member(empty_member).get("enabled") is None
    assert config.member(empty_member).get("enabled", default=True) is True


def test_user_default_override(config, empty_user):
    assert config.user(empty_user).some_value(True) is True
    assert config.user(empty_user).get("some_value") is None
    assert config.user(empty_user).get("some_value", default=True) is True
#endregion


#region Setting Values
@pytest.mark.asyncio
async def test_set_global(config):
    await config.set("enabled", True)
    assert config.enabled() is True


@pytest.mark.asyncio
async def test_set_guild(config, empty_guild):
    await config.guild(empty_guild).set("enabled", True)
    assert config.guild(empty_guild).enabled() is True

    curr_list = config.guild(empty_guild).some_list([1, 2, 3])
    assert curr_list == [1, 2, 3]
    curr_list.append(4)

    await config.guild(empty_guild).set("some_list", curr_list)
    assert config.guild(empty_guild).some_list() == curr_list


@pytest.mark.asyncio
async def test_set_channel(config, empty_channel):
    await config.channel(empty_channel).set("enabled", True)
    assert config.channel(empty_channel).enabled() is True


@pytest.mark.asyncio
async def test_set_channel_no_register(config, empty_channel):
    await config.channel(empty_channel).set("no_register", True)
    assert config.channel(empty_channel).no_register() is True
#endregion
