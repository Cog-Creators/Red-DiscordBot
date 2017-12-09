class Connect:
    """
    This class wraps :func:`~websockets.client.connect` on Python ≥ 3.5.

    This allows using it as an asynchronous context manager.

    """
    def __init__(self, *args, **kwargs):
        self.client = self.__class__.__wrapped__(*args, **kwargs)

    async def __aenter__(self):
        self.websocket = await self
        return self.websocket

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.websocket.close()

    def __await__(self):
        return (yield from self.client)

    __iter__ = __await__
