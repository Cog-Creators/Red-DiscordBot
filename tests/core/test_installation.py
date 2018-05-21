import pytest


@pytest.mark.asyncio
async def test_can_init_bot(red):
    assert red is not None
