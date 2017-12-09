"""
The :mod:`websockets.client` module defines a simple WebSocket client API.

"""

import asyncio
import collections.abc

from .exceptions import InvalidHandshake, InvalidMessage, InvalidStatusCode
from .handshake import build_request, check_response
from .http import USER_AGENT, build_headers, read_response
from .protocol import CONNECTING, OPEN, WebSocketCommonProtocol
from .uri import parse_uri


__all__ = ['connect', 'WebSocketClientProtocol']


class WebSocketClientProtocol(WebSocketCommonProtocol):
    """
    Complete WebSocket client implementation as an :class:`asyncio.Protocol`.

    This class inherits most of its methods from
    :class:`~websockets.protocol.WebSocketCommonProtocol`.

    """
    is_client = True
    state = CONNECTING

    @asyncio.coroutine
    def write_http_request(self, path, headers):
        """
        Write request line and headers to the HTTP request.

        """
        self.path = path
        self.request_headers = build_headers(headers)
        self.raw_request_headers = headers

        # Since the path and headers only contain ASCII characters,
        # we can keep this simple.
        request = ['GET {path} HTTP/1.1'.format(path=path)]
        request.extend('{}: {}'.format(k, v) for k, v in headers)
        request.append('\r\n')
        request = '\r\n'.join(request).encode()

        self.writer.write(request)

    @asyncio.coroutine
    def read_http_response(self):
        """
        Read status line and headers from the HTTP response.

        Raise :exc:`~websockets.exceptions.InvalidMessage` if the HTTP message
        is malformed or isn't an HTTP/1.1 GET request.

        Don't attempt to read the response body because WebSocket handshake
        responses don't have one. If the response contains a body, it may be
        read from ``self.reader`` after this coroutine returns.

        """
        try:
            status_code, headers = yield from read_response(self.reader)
        except ValueError as exc:
            raise InvalidMessage("Malformed HTTP message") from exc

        self.response_headers = build_headers(headers)
        self.raw_response_headers = headers

        return status_code, self.response_headers

    def process_subprotocol(self, get_header, subprotocols=None):
        """
        Handle the Sec-WebSocket-Protocol HTTP header.

        """
        subprotocol = get_header('Sec-WebSocket-Protocol')
        if subprotocol:
            if subprotocols is None or subprotocol not in subprotocols:
                raise InvalidHandshake(
                    "Unknown subprotocol: {}".format(subprotocol))
            return subprotocol

    @asyncio.coroutine
    def handshake(self, wsuri,
                  origin=None, subprotocols=None, extra_headers=None):
        """
        Perform the client side of the opening handshake.

        If provided, ``origin`` sets the Origin HTTP header.

        If provided, ``subprotocols`` is a list of supported subprotocols in
        order of decreasing preference.

        If provided, ``extra_headers`` sets additional HTTP request headers.
        It must be a mapping or an iterable of (name, value) pairs.

        """
        headers = []
        set_header = lambda k, v: headers.append((k, v))

        if wsuri.port == (443 if wsuri.secure else 80):     # pragma: no cover
            set_header('Host', wsuri.host)
        else:
            set_header('Host', '{}:{}'.format(wsuri.host, wsuri.port))
        if origin is not None:
            set_header('Origin', origin)
        if subprotocols is not None:
            set_header('Sec-WebSocket-Protocol', ', '.join(subprotocols))
        if extra_headers is not None:
            if isinstance(extra_headers, collections.abc.Mapping):
                extra_headers = extra_headers.items()
            for name, value in extra_headers:
                set_header(name, value)
        set_header('User-Agent', USER_AGENT)

        key = build_request(set_header)

        yield from self.write_http_request(wsuri.resource_name, headers)

        status_code, headers = yield from self.read_http_response()
        get_header = lambda k: headers.get(k, '')

        if status_code != 101:
            raise InvalidStatusCode(status_code)

        check_response(get_header, key)

        self.subprotocol = self.process_subprotocol(get_header, subprotocols)

        assert self.state == CONNECTING
        self.state = OPEN
        self.opening_handshake.set_result(True)


@asyncio.coroutine
def connect(uri, *,
            create_protocol=None,
            timeout=10, max_size=2 ** 20, max_queue=2 ** 5,
            read_limit=2 ** 16, write_limit=2 ** 16,
            loop=None, legacy_recv=False, klass=None,
            origin=None, subprotocols=None, extra_headers=None,
            **kwds):
    """
    This coroutine connects to a WebSocket server at a given ``uri``.

    It yields a :class:`WebSocketClientProtocol` which can then be used to
    send and receive messages.

    :func:`connect` is a wrapper around the event loop's
    :meth:`~asyncio.BaseEventLoop.create_connection` method. Unknown keyword
    arguments are passed to :meth:`~asyncio.BaseEventLoop.create_connection`.

    For example, you can set the ``ssl`` keyword argument to a
    :class:`~ssl.SSLContext` to enforce some TLS settings. When connecting to
    a ``wss://`` URI, if this argument isn't provided explicitly, it's set to
    ``True``, which means Python's default :class:`~ssl.SSLContext` is used.

    The behavior of the ``timeout``, ``max_size``, and ``max_queue``,
    ``read_limit``, and ``write_limit`` optional arguments is described in the
    documentation of :class:`~websockets.protocol.WebSocketCommonProtocol`.

    The ``create_protocol`` parameter allows customizing the asyncio protocol
    that manages the connection. It should be a callable or class accepting
    the same arguments as :class:`WebSocketClientProtocol` and returning a
    :class:`WebSocketClientProtocol` instance. It defaults to
    :class:`WebSocketClientProtocol`.

    :func:`connect` also accepts the following optional arguments:

    * ``origin`` sets the Origin HTTP header
    * ``subprotocols`` is a list of supported subprotocols in order of
      decreasing preference
    * ``extra_headers`` sets additional HTTP request headers – it can be a
      mapping or an iterable of (name, value) pairs

    :func:`connect` raises :exc:`~websockets.uri.InvalidURI` if ``uri`` is
    invalid and :exc:`~websockets.handshake.InvalidHandshake` if the opening
    handshake fails.

    On Python 3.5, :func:`connect` can be used as a asynchronous context
    manager. In that case, the connection is closed when exiting the context.

    """
    if loop is None:
        loop = asyncio.get_event_loop()

    # Backwards-compatibility: create_protocol used to be called klass.
    # In the unlikely event that both are specified, klass is ignored.
    if create_protocol is None:
        create_protocol = klass

    if create_protocol is None:
        create_protocol = WebSocketClientProtocol

    wsuri = parse_uri(uri)
    if wsuri.secure:
        kwds.setdefault('ssl', True)
    elif kwds.get('ssl') is not None:
        raise ValueError("connect() received a SSL context for a ws:// URI. "
                         "Use a wss:// URI to enable TLS.")
    factory = lambda: create_protocol(
        host=wsuri.host, port=wsuri.port, secure=wsuri.secure,
        timeout=timeout, max_size=max_size, max_queue=max_queue,
        read_limit=read_limit, write_limit=write_limit,
        loop=loop, legacy_recv=legacy_recv,
    )

    transport, protocol = yield from loop.create_connection(
        factory, wsuri.host, wsuri.port, **kwds)

    try:
        yield from protocol.handshake(
            wsuri, origin=origin, subprotocols=subprotocols,
            extra_headers=extra_headers)
    except Exception:
        yield from protocol.close_connection(force=True)
        raise

    return protocol


try:
    from .py35.client import Connect
except (SyntaxError, ImportError):                          # pragma: no cover
    pass
else:
    Connect.__wrapped__ = connect
    # Copy over docstring to support building documentation on Python 3.5.
    Connect.__doc__ = connect.__doc__
    connect = Connect
