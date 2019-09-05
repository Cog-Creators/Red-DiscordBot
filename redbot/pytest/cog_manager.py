# Red Dependencies
import pytest

__all__ = ["cog_mgr", "default_dir"]


@pytest.fixture()
def cog_mgr(red):
    return red.cog_mgr


@pytest.fixture()
def default_dir(red):
    return red.main_dir
