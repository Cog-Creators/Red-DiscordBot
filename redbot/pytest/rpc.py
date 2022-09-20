from unittest.mock import MagicMock

import pytest

from redbot.core.rpc import RPC, RPCMixin

__all__ = ["rpc", "rpcmixin", "cog", "existing_func", "existing_multi_func"]


@pytest.fixture()
async def rpc():
    rpc = RPC()
    await rpc._pre_login()
    return rpc


@pytest.fixture()
def rpcmixin():
    r = RPCMixin()
    r.rpc = MagicMock(spec=RPC)
    return r


@pytest.fixture()
def cog():
    class Cog:
        async def cofunc(self, *args, **kwargs):
            pass

        async def cofunc2(self, *args, **kwargs):
            pass

        async def cofunc3(self, *args, **kwargs):
            pass

        def func(self, *args, **kwargs):
            pass

    return Cog()


@pytest.fixture()
def existing_func(rpc, cog):
    rpc.add_method(cog.cofunc)

    return cog.cofunc


@pytest.fixture()
def existing_multi_func(rpc, cog):
    funcs = [cog.cofunc, cog.cofunc2, cog.cofunc3]
    rpc.add_multi_method(*funcs)

    return funcs
