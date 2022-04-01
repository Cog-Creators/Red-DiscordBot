import pytest
from bluebot.core import bank as bank_module

__all__ = ["bank"]


@pytest.fixture()
async def bank(config, monkeypatch):
    from bluebot.core import Config

    with monkeypatch.context() as m:
        m.setattr(Config, "get_conf", lambda *args, **kwargs: config)
        # Heh. Except maybe cotton candy.
        await bank_module._init()
        return bank_module
