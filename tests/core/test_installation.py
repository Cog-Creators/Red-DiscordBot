import pytest


@pytest.mark.asyncio
async def test_can_init_bot(blue):
    assert blue is not None
