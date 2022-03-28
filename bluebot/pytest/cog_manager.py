import pytest

__all__ = ["cog_mgr", "default_dir"]


@pytest.fixture()
def cog_mgr(blue):
    return blue._cog_mgr


@pytest.fixture()
def default_dir(blue):
    return blue._main_dir
