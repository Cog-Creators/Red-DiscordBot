import pytest

from redbot.core.drivers import IdentifierData
from redbot.core.drivers.cache import ConfigDriverCache


@pytest.fixture()
def driver_cache():
    return ConfigDriverCache()


def test_driver_cache_simple(driver_cache):
    _id = IdentifierData("Core", "0", "GLOBAL", (), ("prefix",), 0, False)
    driver_cache[_id] = "!"
    assert driver_cache[_id] == "!"

    del driver_cache[_id]
    with pytest.raises(KeyError):
        _ = driver_cache[_id]


def test_driver_cache_cached_parent(driver_cache):
    # Test with identifiers
    _id1 = IdentifierData("Core", "0", "GLOBAL", (), ("id1",), 0, False)
    driver_cache[_id1] = {"id2": True}
    assert driver_cache[_id1] == {"id2": True}
    _id2 = _id1.add_identifier("id2")
    assert driver_cache[_id2] is True
    driver_cache[_id2] = False
    assert driver_cache[_id2] is False
    assert driver_cache[_id1] == {"id2": False}

    # Test with primary keys
    _id1 = IdentifierData("Core", "0", "MEMBER", ("1234",), (), 0, False)
    driver_cache[_id1] = {"5678": {"id": True}}
    assert driver_cache[_id1] == {"5678": {"id": True}}
    _id2 = IdentifierData("Core", "0", "MEMBER", ("1234", "5678"), (), 0, False)
    assert driver_cache[_id2] == {"id": True}
    driver_cache[_id2] = {"id": False}
    assert driver_cache[_id2] == {"id": False}
    assert driver_cache[_id1] == {"5678": {"id": False}}
    _id3 = _id2.add_identifier("id")
    assert driver_cache[_id3] is False
    driver_cache[_id3] = None
    assert driver_cache[_id3] is None
    assert driver_cache[_id2] == {"id": None}
    assert driver_cache[_id1] == {"5678": {"id": None}}

    # Test across primary keys and identifiers
    _id1 = IdentifierData("Core", "0", "GUILD", ("1234",), (), 0, False)
    driver_cache[_id1] = {"id": True}
    assert driver_cache[_id1] == {"id": True}
    _id2 = _id1.add_identifier("id")
    assert driver_cache[_id2] is True
    driver_cache[_id2] = False
    assert driver_cache[_id2] is False
    assert driver_cache[_id1] == {"id": False}
