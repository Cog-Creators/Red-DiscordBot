import pytest

__all__ = ["cog_mgr", "default_dir"]


@pytest.fixture()
def cog_mgr(red):
    return red._cog_mgr


@pytest.fixture()
def default_dir(red):
    return red._main_dir
