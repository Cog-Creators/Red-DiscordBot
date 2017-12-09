import asyncio
import contextlib
import functools
import logging
import os
import ssl
import sys
import unittest
import unittest.mock
import urllib.request

from .client import *
from .compatibility import FORBIDDEN, OK, UNAUTHORIZED
from .exceptions import ConnectionClosed, InvalidHandshake, InvalidStatusCode
from .http import USER_AGENT, read_response
from .server import *


# Avoid displaying stack traces at the ERROR logging level.
logging.basicConfig(level=logging.CRITICAL)

testcert = os.path.join(os.path.dirname(__file__), 'testcert.pem')


@asyncio.coroutine
def handler(ws, path):
    if path == '/attributes':
        yield from ws.send(repr((ws.host, ws.port, ws.secure)))
    elif path == '/path':
        yield from ws.send(str(ws.path))
    elif path == '/headers':
        yield from ws.send(str(ws.request_headers))
        yield from ws.send(str(ws.response_headers))
    elif path == '/raw_headers':
        yield from ws.send(repr(ws.raw_request_headers))
        yield from ws.send(repr(ws.raw_response_headers))
    elif path == '/subprotocol':
        yield from ws.send(repr(ws.subprotocol))
    else:
        yield from ws.send((yield from ws.recv()))


@contextlib.contextmanager
def temp_test_server(test, **kwds):
    test.start_server(**kwds)
    try:
        yield
    finally:
        test.stop_server()


@contextlib.contextmanager
def temp_test_client(test, *args, **kwds):
    test.start_client(*args, **kwds)
    try:
        yield
    finally:
        test.stop_client()


def with_manager(manager, *args, **kwds):
    """
    Return a decorator that wraps a function with a context manager.
    """
    def decorate(func):
        @functools.wraps(func)
        def _decorate(self, *_args, **_kwds):
            with manager(self, *args, **kwds):
                return func(self, *_args, **_kwds)

        return _decorate

    return decorate


def with_server(**kwds):
    """
    Return a decorator for TestCase methods that starts and stops a server.
    """
    return with_manager(temp_test_server, **kwds)


def with_client(*args, **kwds):
    """
    Return a decorator for TestCase methods that starts and stops a client.
    """
    return with_manager(temp_test_client, *args, **kwds)


class UnauthorizedServerProtocol(WebSocketServerProtocol):

    @asyncio.coroutine
    def process_request(self, path, request_headers):
        return UNAUTHORIZED, []


class ForbiddenServerProtocol(WebSocketServerProtocol):

    @asyncio.coroutine
    def process_request(self, path, request_headers):
        return FORBIDDEN, []


class HealthCheckServerProtocol(WebSocketServerProtocol):

    @asyncio.coroutine
    def process_request(self, path, request_headers):
        if path == '/__health__/':
            body = b'status = green\n'
            return OK, [('Content-Length', str(len(body)))], body


class FooClientProtocol(WebSocketClientProtocol):
    pass


class BarClientProtocol(WebSocketClientProtocol):
    pass


class ClientServerTests(unittest.TestCase):

    secure = False

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def run_loop_once(self):
        # Process callbacks scheduled with call_soon by appending a callback
        # to stop the event loop then running it until it hits that callback.
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()

    def start_server(self, **kwds):
        server = serve(handler, 'localhost', 8642, **kwds)
        self.server = self.loop.run_until_complete(server)

    def start_client(self, path='', **kwds):
        client = connect('ws://localhost:8642/' + path, **kwds)
        self.client = self.loop.run_until_complete(client)

    def stop_client(self):
        try:
            self.loop.run_until_complete(
                asyncio.wait_for(self.client.worker_task, timeout=1))
        except asyncio.TimeoutError:                # pragma: no cover
            self.fail("Client failed to stop")

    def stop_server(self):
        self.server.close()
        try:
            self.loop.run_until_complete(
                asyncio.wait_for(self.server.wait_closed(), timeout=1))
        except asyncio.TimeoutError:                # pragma: no cover
            self.fail("Server failed to stop")

    @contextlib.contextmanager
    def temp_server(self, **kwds):
        with temp_test_server(self, **kwds):
            yield

    @contextlib.contextmanager
    def temp_client(self, *args, **kwds):
        with temp_test_client(self, *args, **kwds):
            yield

    @with_server()
    @with_client()
    def test_basic(self):
        self.loop.run_until_complete(self.client.send("Hello!"))
        reply = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(reply, "Hello!")

    @with_server()
    def test_server_close_while_client_connected(self):
        self.start_client()

    def test_explicit_event_loop(self):
        with self.temp_server(loop=self.loop):
            with self.temp_client(loop=self.loop):
                self.loop.run_until_complete(self.client.send("Hello!"))
                reply = self.loop.run_until_complete(self.client.recv())
                self.assertEqual(reply, "Hello!")

    @with_server()
    @with_client('attributes')
    def test_protocol_attributes(self):
        expected_attrs = ('localhost', 8642, self.secure)
        client_attrs = (self.client.host, self.client.port, self.client.secure)
        self.assertEqual(client_attrs, expected_attrs)
        server_attrs = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_attrs, repr(expected_attrs))

    @with_server()
    @with_client('path')
    def test_protocol_path(self):
        client_path = self.client.path
        self.assertEqual(client_path, '/path')
        server_path = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_path, '/path')

    @with_server()
    @with_client('headers')
    def test_protocol_headers(self):
        client_req = self.client.request_headers
        client_resp = self.client.response_headers
        self.assertEqual(client_req['User-Agent'], USER_AGENT)
        self.assertEqual(client_resp['Server'], USER_AGENT)
        server_req = self.loop.run_until_complete(self.client.recv())
        server_resp = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_req, str(client_req))
        self.assertEqual(server_resp, str(client_resp))

    @with_server()
    @with_client('raw_headers')
    def test_protocol_raw_headers(self):
        client_req = self.client.raw_request_headers
        client_resp = self.client.raw_response_headers
        self.assertEqual(dict(client_req)['User-Agent'], USER_AGENT)
        self.assertEqual(dict(client_resp)['Server'], USER_AGENT)
        server_req = self.loop.run_until_complete(self.client.recv())
        server_resp = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_req, repr(client_req))
        self.assertEqual(server_resp, repr(client_resp))

    @with_server()
    @with_client('raw_headers', extra_headers={'X-Spam': 'Eggs'})
    def test_protocol_custom_request_headers_dict(self):
        req_headers = self.loop.run_until_complete(self.client.recv())
        self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", req_headers)

    @with_server()
    @with_client('raw_headers', extra_headers=[('X-Spam', 'Eggs')])
    def test_protocol_custom_request_headers_list(self):
        req_headers = self.loop.run_until_complete(self.client.recv())
        self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", req_headers)

    @with_server(extra_headers=lambda p, r: {'X-Spam': 'Eggs'})
    @with_client('raw_headers')
    def test_protocol_custom_response_headers_callable_dict(self):
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)

    @with_server(extra_headers=lambda p, r: [('X-Spam', 'Eggs')])
    @with_client('raw_headers')
    def test_protocol_custom_response_headers_callable_list(self):
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)

    @with_server(extra_headers={'X-Spam': 'Eggs'})
    @with_client('raw_headers')
    def test_protocol_custom_response_headers_dict(self):
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)

    @with_server(extra_headers=[('X-Spam', 'Eggs')])
    @with_client('raw_headers')
    def test_protocol_custom_response_headers_list(self):
        self.loop.run_until_complete(self.client.recv())
        resp_headers = self.loop.run_until_complete(self.client.recv())
        self.assertIn("('X-Spam', 'Eggs')", resp_headers)

    @with_server(create_protocol=HealthCheckServerProtocol)
    @with_client()
    def test_custom_protocol_http_request(self):
        # One URL returns an HTTP response.

        if self.secure:
            url = 'https://localhost:8642/__health__/'
            if sys.version_info[:2] < (3, 4):               # pragma: no cover
                # Python 3.3 didn't check SSL certificates.
                open_health_check = functools.partial(
                    urllib.request.urlopen, url)
            else:                                           # pragma: no cover
                open_health_check = functools.partial(
                    urllib.request.urlopen, url, context=self.client_context)
        else:
            url = 'http://localhost:8642/__health__/'
            open_health_check = functools.partial(
                urllib.request.urlopen, url)

        response = self.loop.run_until_complete(
            self.loop.run_in_executor(None, open_health_check))

        with contextlib.closing(response):
            self.assertEqual(response.code, 200)
            self.assertEqual(response.read(), b'status = green\n')

        # Other URLs create a WebSocket connection.

        self.loop.run_until_complete(self.client.send("Hello!"))
        reply = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(reply, "Hello!")

    def assert_client_raises_code(self, status_code):
        with self.assertRaises(InvalidStatusCode) as raised:
            self.start_client()
        self.assertEqual(raised.exception.status_code, status_code)

    @with_server(create_protocol=UnauthorizedServerProtocol)
    def test_server_create_protocol(self):
        self.assert_client_raises_code(401)

    @with_server(create_protocol=(lambda *args, **kwargs:
                 UnauthorizedServerProtocol(*args, **kwargs)))
    def test_server_create_protocol_function(self):
        self.assert_client_raises_code(401)

    @with_server(klass=UnauthorizedServerProtocol)
    def test_server_klass(self):
        self.assert_client_raises_code(401)

    @with_server(create_protocol=ForbiddenServerProtocol,
                 klass=UnauthorizedServerProtocol)
    def test_server_create_protocol_over_klass(self):
        self.assert_client_raises_code(403)

    @with_server()
    @with_client('path', create_protocol=FooClientProtocol)
    def test_client_create_protocol(self):
        self.assertIsInstance(self.client, FooClientProtocol)

    @with_server()
    @with_client('path', create_protocol=(
                 lambda *args, **kwargs: FooClientProtocol(*args, **kwargs)))
    def test_client_create_protocol_function(self):
        self.assertIsInstance(self.client, FooClientProtocol)

    @with_server()
    @with_client('path', klass=FooClientProtocol)
    def test_client_klass(self):
        self.assertIsInstance(self.client, FooClientProtocol)

    @with_server()
    @with_client('path', create_protocol=BarClientProtocol,
                 klass=FooClientProtocol)
    def test_client_create_protocol_over_klass(self):
        self.assertIsInstance(self.client, BarClientProtocol)

    @with_server()
    @with_client('subprotocol')
    def test_no_subprotocol(self):
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)

    @with_server(subprotocols=['superchat', 'chat'])
    @with_client('subprotocol', subprotocols=['otherchat', 'chat'])
    def test_subprotocol_found(self):
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr('chat'))
        self.assertEqual(self.client.subprotocol, 'chat')

    @with_server(subprotocols=['superchat'])
    @with_client('subprotocol', subprotocols=['otherchat'])
    def test_subprotocol_not_found(self):
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)

    @with_server()
    @with_client('subprotocol', subprotocols=['otherchat', 'chat'])
    def test_subprotocol_not_offered(self):
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)

    @with_server(subprotocols=['superchat', 'chat'])
    @with_client('subprotocol')
    def test_subprotocol_not_requested(self):
        server_subprotocol = self.loop.run_until_complete(self.client.recv())
        self.assertEqual(server_subprotocol, repr(None))
        self.assertEqual(self.client.subprotocol, None)

    @with_server(subprotocols=['superchat'])
    @unittest.mock.patch.object(WebSocketServerProtocol, 'select_subprotocol')
    def test_subprotocol_error(self, _select_subprotocol):
        _select_subprotocol.return_value = 'superchat'

        with self.assertRaises(InvalidHandshake):
            self.start_client('subprotocol', subprotocols=['otherchat'])
        self.run_loop_once()

    @with_server()
    @unittest.mock.patch('websockets.server.read_request')
    def test_server_receives_malformed_request(self, _read_request):
        _read_request.side_effect = ValueError("read_request failed")

        with self.assertRaises(InvalidHandshake):
            self.start_client()

    @with_server()
    @unittest.mock.patch('websockets.client.read_response')
    def test_client_receives_malformed_response(self, _read_response):
        _read_response.side_effect = ValueError("read_response failed")

        with self.assertRaises(InvalidHandshake):
            self.start_client()
        self.run_loop_once()

    @with_server()
    @unittest.mock.patch('websockets.client.build_request')
    def test_client_sends_invalid_handshake_request(self, _build_request):
        def wrong_build_request(set_header):
            return '42'
        _build_request.side_effect = wrong_build_request

        with self.assertRaises(InvalidHandshake):
            self.start_client()

    @with_server()
    @unittest.mock.patch('websockets.server.build_response')
    def test_server_sends_invalid_handshake_response(self, _build_response):
        def wrong_build_response(set_header, key):
            return build_response(set_header, '42')
        _build_response.side_effect = wrong_build_response

        with self.assertRaises(InvalidHandshake):
            self.start_client()

    @with_server()
    @unittest.mock.patch('websockets.client.read_response')
    def test_server_does_not_switch_protocols(self, _read_response):
        @asyncio.coroutine
        def wrong_read_response(stream):
            status_code, headers = yield from read_response(stream)
            return 400, headers
        _read_response.side_effect = wrong_read_response

        with self.assertRaises(InvalidStatusCode):
            self.start_client()
        self.run_loop_once()

    @with_server()
    @unittest.mock.patch('websockets.server.WebSocketServerProtocol.send')
    def test_server_handler_crashes(self, send):
        send.side_effect = ValueError("send failed")

        with self.temp_client():
            self.loop.run_until_complete(self.client.send("Hello!"))
            with self.assertRaises(ConnectionClosed):
                self.loop.run_until_complete(self.client.recv())

        # Connection ends with an unexpected error.
        self.assertEqual(self.client.close_code, 1011)

    @with_server()
    @unittest.mock.patch('websockets.server.WebSocketServerProtocol.close')
    def test_server_close_crashes(self, close):
        close.side_effect = ValueError("close failed")

        with self.temp_client():
            self.loop.run_until_complete(self.client.send("Hello!"))
            reply = self.loop.run_until_complete(self.client.recv())
            self.assertEqual(reply, "Hello!")

        # Connection ends with an abnormal closure.
        self.assertEqual(self.client.close_code, 1006)

    @with_server()
    @with_client()
    @unittest.mock.patch.object(WebSocketClientProtocol, 'handshake')
    def test_client_closes_connection_before_handshake(self, handshake):
        # We have mocked the handshake() method to prevent the client from
        # performing the opening handshake. Force it to close the connection.
        self.loop.run_until_complete(self.client.close_connection(force=True))
        # The server should stop properly anyway. It used to hang because the
        # worker handling the connection was waiting for the opening handshake.

    @with_server()
    @unittest.mock.patch('websockets.server.read_request')
    def test_server_shuts_down_during_opening_handshake(self, _read_request):
        _read_request.side_effect = asyncio.CancelledError

        self.server.closing = True
        with self.assertRaises(InvalidHandshake) as raised:
            self.start_client()

        # Opening handshake fails with 503 Service Unavailable
        self.assertEqual(str(raised.exception), "Status code not 101: 503")

    @with_server()
    def test_server_shuts_down_during_connection_handling(self):
        with self.temp_client():
            self.server.close()
            with self.assertRaises(ConnectionClosed):
                self.loop.run_until_complete(self.client.recv())

        # Websocket connection terminates with 1001 Going Away.
        self.assertEqual(self.client.close_code, 1001)

    @with_server(create_protocol=ForbiddenServerProtocol)
    def test_invalid_status_error_during_client_connect(self):
        with self.assertRaises(InvalidStatusCode) as raised:
            self.start_client()
        exception = raised.exception
        self.assertEqual(str(exception), "Status code not 101: 403")
        self.assertEqual(exception.status_code, 403)

    @with_server()
    @unittest.mock.patch('websockets.server.read_request')
    def test_connection_error_during_opening_handshake(self, _read_request):
        _read_request.side_effect = ConnectionError

        # Exception appears to be platform-dependent: InvalidHandshake on
        # macOS, ConnectionResetError on Linux. This doesn't matter; this
        # test primarily aims at covering a code path on the server side.
        with self.assertRaises(Exception):
            self.start_client()

    @with_server()
    @unittest.mock.patch('websockets.server.WebSocketServerProtocol.close')
    def test_connection_error_during_closing_handshake(self, close):
        close.side_effect = ConnectionError

        with self.temp_client():
            self.loop.run_until_complete(self.client.send("Hello!"))
            reply = self.loop.run_until_complete(self.client.recv())
            self.assertEqual(reply, "Hello!")

        # Connection ends with an abnormal closure.
        self.assertEqual(self.client.close_code, 1006)


@unittest.skipUnless(os.path.exists(testcert), "test certificate is missing")
class SSLClientServerTests(ClientServerTests):

    secure = True

    @property
    def server_context(self):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        ssl_context.load_cert_chain(testcert)
        return ssl_context

    @property
    def client_context(self):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        ssl_context.load_verify_locations(testcert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        return ssl_context

    def start_server(self, *args, **kwds):
        kwds['ssl'] = self.server_context
        server = serve(handler, 'localhost', 8642, **kwds)
        self.server = self.loop.run_until_complete(server)

    def start_client(self, path='', **kwds):
        kwds['ssl'] = self.client_context
        client = connect('wss://localhost:8642/' + path, **kwds)
        self.client = self.loop.run_until_complete(client)

    @with_server()
    def test_ws_uri_is_rejected(self):
        client = connect('ws://localhost:8642/', ssl=self.client_context)
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(client)


class ClientServerOriginTests(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_checking_origin_succeeds(self):
        server = self.loop.run_until_complete(
            serve(handler, 'localhost', 8642, origins=['http://localhost']))
        client = self.loop.run_until_complete(
            connect('ws://localhost:8642/', origin='http://localhost'))

        self.loop.run_until_complete(client.send("Hello!"))
        self.assertEqual(self.loop.run_until_complete(client.recv()), "Hello!")

        self.loop.run_until_complete(client.close())
        server.close()
        self.loop.run_until_complete(server.wait_closed())

    def test_checking_origin_fails(self):
        server = self.loop.run_until_complete(
            serve(handler, 'localhost', 8642, origins=['http://localhost']))
        with self.assertRaisesRegex(InvalidHandshake,
                                    "Status code not 101: 403"):
            self.loop.run_until_complete(
                connect('ws://localhost:8642/', origin='http://otherhost'))

        server.close()
        self.loop.run_until_complete(server.wait_closed())

    def test_checking_lack_of_origin_succeeds(self):
        server = self.loop.run_until_complete(
            serve(handler, 'localhost', 8642, origins=['']))
        client = self.loop.run_until_complete(connect('ws://localhost:8642/'))

        self.loop.run_until_complete(client.send("Hello!"))
        self.assertEqual(self.loop.run_until_complete(client.recv()), "Hello!")

        self.loop.run_until_complete(client.close())
        server.close()
        self.loop.run_until_complete(server.wait_closed())


try:
    from .py35.client_server import ClientServerContextManager
except (SyntaxError, ImportError):                          # pragma: no cover
    pass
else:
    class ClientServerContextManagerTests(ClientServerContextManager,
                                          unittest.TestCase):
        pass
