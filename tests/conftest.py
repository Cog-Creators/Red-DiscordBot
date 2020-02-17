import os

import pytest
from redbot.core import drivers, data_manager

from redbot._event_loop_handlers import new_main_event_loop


@pytest.fixture(scope="session")
def event_loop(request):
    """Create an instance of the default event loop for entire session."""
    with new_main_event_loop() as loop:
        yield loop


def _get_backend_type():
    if os.getenv("RED_STORAGE_TYPE") == "postgres":
        return drivers.BackendType.POSTGRES
    else:
        return drivers.BackendType.JSON


@pytest.fixture(scope="session", autouse=True)
async def _setup_driver():
    backend_type = _get_backend_type()
    storage_details = {}
    data_manager.storage_type = lambda: backend_type.value
    data_manager.storage_details = lambda: storage_details
    driver_cls = drivers.get_driver_class(backend_type)
    await driver_cls.initialize(**storage_details)
    yield
    await driver_cls.teardown()
