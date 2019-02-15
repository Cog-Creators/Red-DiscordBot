import pytest
from redbot.core import modlog

__all__ = ["mod"]


@pytest.fixture
def mod(config, monkeypatch):
    from redbot.core import Config

    with monkeypatch.context() as m:
        m.setattr(Config, "get_conf", lambda *args, **kwargs: config)

        modlog._init()
        return modlog
