import pytest

from redbot.cogs.audio import Audio
from redbot.core import Config

__all__ = ["audio"]


@pytest.fixture()
def audio(config, monkeypatch, red):
    with monkeypatch.context() as m:
        m.setattr(Config, "get_conf", lambda *args, **kwargs: config)

        Audio._init(red)
        return Audio
