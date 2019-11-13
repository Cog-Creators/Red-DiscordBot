import pytest

from redbot.core import data_manager

__all__ = ["cleanup_datamanager", "data_mgr_config", "cog_instance"]


@pytest.fixture(autouse=True)
def cleanup_datamanager():
    data_manager.basic_config = None


@pytest.fixture()
def data_mgr_config(tmpdir):
    default = data_manager.basic_config_default.copy()
    default["BASE_DIR"] = str(tmpdir)
    return default


@pytest.fixture()
def cog_instance():
    thing = type("CogTest", (object,), {})
    return thing()
