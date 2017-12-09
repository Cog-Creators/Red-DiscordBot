# Tests containing Python 3.5+ syntax, extracted from test_client_server.py.
# To avoid test discovery, this module's name must not start with test_.

import asyncio

from ..client import *
from ..server import *
from ..test_client_server import handler


class ClientServerContextManager:

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_client(self):
        server = serve(handler, 'localhost', 8642)
        self.server = self.loop.run_until_complete(server)

        async def run_client():
            async with connect('ws://localhost:8642/') as client:
                await client.send("Hello!")
                reply = await client.recv()
                self.assertEqual(reply, "Hello!")

        self.loop.run_until_complete(run_client())

        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())

    def test_server(self):
        async def run_server():
            async with serve(handler, 'localhost', 8642):
                client = await connect('ws://localhost:8642/')
                await client.send("Hello!")
                reply = await client.recv()
                self.assertEqual(reply, "Hello!")

        self.loop.run_until_complete(run_server())
