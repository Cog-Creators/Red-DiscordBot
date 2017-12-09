class Serve:
    """
    This class wraps :func:`~websockets.server.serve` on Python ≥ 3.5.

    This allows using it as an asynchronous context manager.

    """
    def __init__(self, *args, **kwargs):
        self.server = self.__class__.__wrapped__(*args, **kwargs)

    async def __aenter__(self):
        self.server = await self
        return self.server

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.server.close()
        await self.server.wait_closed()

    def __await__(self):
        return (yield from self.server)

    __iter__ = __await__
