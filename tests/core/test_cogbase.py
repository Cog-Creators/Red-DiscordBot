import pytest

from redbot.core import CogBase
from redbot.core.rpc import get_name


class Cog(CogBase):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(bot)

        self.add_rpc_methods(
            self.rpc_handler
        )

    async def rpc_handler(self):
        pass


def test_cogbase_unload(red):
    c = Cog(red)
    name = get_name(c.rpc_handler)

    assert name in red.rpc._rpc.methods
    count = len(red.rpc._rpc.methods)

    c._CogBase__unload()

    assert name not in red.rpc._rpc.methods
    assert count - 1 == len(red.rpc._rpc.methods)
