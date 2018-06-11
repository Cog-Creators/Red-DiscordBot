import pytest


@pytest.fixture()
def bank(config, monkeypatch):
    from redbot.core import Config

    with monkeypatch.context() as m:
        m.setattr(Config, "get_conf", lambda *args, **kwargs: config)
        from redbot.core import bank

        bank._register_defaults()
        return bank