"""
The :mod:`websockets.protocol` module handles WebSocket control and data
frames as specified in `sections 4 to 8 of RFC 6455`_.

.. _sections 4 to 8 of RFC 6455: http://tools.ietf.org/html/rfc6455#section-4

"""

import asyncio
import asyncio.queues
import codecs
import collections
import logging
import random
import struct

from .compatibility import asyncio_ensure_future
from .exceptions import (
    ConnectionClosed, InvalidState, PayloadTooBig, WebSocketProtocolError
)
from .framing import *
from .handshake import *


__all__ = ['WebSocketCommonProtocol']

logger = logging.getLogger(__name__)


# A WebSocket connection goes through the following four states, in order:

CONNECTING, OPEN, CLOSING, CLOSED = range(4)

# In order to ensure consistency, the code always checks the current value of
# WebSocketCommonProtocol.state before assigning a new value and never yields
# between the check and the assignment.


class WebSocketCommonProtocol(asyncio.StreamReaderProtocol):
    """
    This class implements common parts of the WebSocket protocol.

    It assumes that the WebSocket connection is established. The handshake is
    managed in subclasses such as
    :class:`~websockets.server.WebSocketServerProtocol` and
    :class:`~websockets.client.WebSocketClientProtocol`.

    It runs a task that stores incoming data frames in a queue and deals with
    control frames automatically. It sends outgoing data frames and performs
    the closing handshake.

    The ``host``, ``port`` and ``secure`` parameters are simply stored as
    attributes for handlers that need them.

    The ``timeout`` parameter defines the maximum wait time in seconds for
    completing the closing handshake and, only on the client side, for
    terminating the TCP connection. :meth:`close()` will complete in at most
    this time on the server side and twice this time on the client side.

    The ``max_size`` parameter enforces the maximum size for incoming messages
    in bytes. The default value is 1MB. ``None`` disables the limit. If a
    message larger than the maximum size is received, :meth:`recv()` will
    raise :exc:`~websockets.exceptions.ConnectionClosed` and the connection
    will be closed with status code 1009.

    The ``max_queue`` parameter sets the maximum length of the queue that holds
    incoming messages. The default value is 32. 0 disables the limit. Messages
    are added to an in-memory queue when they're received; then :meth:`recv()`
    pops from that queue. In order to prevent excessive memory consumption when
    messages are received faster than they can be processed, the queue must be
    bounded. If the queue fills up, the protocol stops processing incoming data
    until :meth:`recv()` is called. In this situation, various receive buffers
    (at least in ``asyncio`` and in the OS) will fill up, then the TCP receive
    window will shrink, slowing down transmission to avoid packet loss.

    Since Python can use up to 4 bytes of memory to represent a single
    character, each websocket connection may use up to ``4 * max_size *
    max_queue`` bytes of memory to store incoming messages. By default,
    this is 128MB. You may want to lower the limits, depending on your
    application's requirements.

    The ``read_limit`` argument sets the high-water limit of the buffer for
    incoming bytes. The low-water limit is half the high-water limit. The
    default value is 64kB, half of asyncio's default (based on the current
    implementation of :class:`~asyncio.StreamReader`).

    The ``write_limit`` argument sets the high-water limit of the buffer for
    outgoing bytes. The low-water limit is a quarter of the high-water limit.
    The default value is 64kB, equal to asyncio's default (based on the
    current implementation of ``_FlowControlMixin``).

    As soon as the HTTP request and response in the opening handshake are
    processed, the request path is available in the :attr:`path` attribute,
    and the request and response HTTP headers are available:

    * as a :class:`~http.client.HTTPMessage` in the :attr:`request_headers`
      and :attr:`response_headers` attributes
    * as an iterable of (name, value) pairs in the :attr:`raw_request_headers`
      and :attr:`raw_response_headers` attributes

    These attributes must be treated as immutable.

    If a subprotocol was negotiated, it's available in the :attr:`subprotocol`
    attribute.

    Once the connection is closed, the status code is available in the
    :attr:`close_code` attribute and the reason in :attr:`close_reason`.

    """
    # There are only two differences between the client-side and the server-
    # side behavior: masking the payload and closing the underlying TCP
    # connection. This class implements the server-side behavior by default.
    # To get the client-side behavior, set is_client = True.

    is_client = False
    state = OPEN

    def __init__(self, *,
                 host=None, port=None, secure=None,
                 timeout=10, max_size=2 ** 20, max_queue=2 ** 5,
                 read_limit=2 ** 16, write_limit=2 ** 16,
                 loop=None, legacy_recv=False):
        self.host = host
        self.port = port
        self.secure = secure
        self.timeout = timeout
        self.max_size = max_size
        self.max_queue = max_queue
        self.read_limit = read_limit
        self.write_limit = write_limit

        # Store a reference to loop to avoid relying on self._loop, a private
        # attribute of StreamReaderProtocol, inherited from _FlowControlMixin.
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop

        self.legacy_recv = legacy_recv

        # This limit is both the line length limit and half the buffer limit.
        stream_reader = asyncio.StreamReader(limit=read_limit // 2, loop=loop)
        super().__init__(stream_reader, self.client_connected, loop)

        self.reader = None
        self.writer = None
        self._drain_lock = asyncio.Lock(loop=loop)

        self.path = None
        self.request_headers = None
        self.raw_request_headers = None
        self.response_headers = None
        self.raw_response_headers = None

        self.subprotocol = None

        # Code and reason must be set when the closing handshake completes.
        self.close_code = None
        self.close_reason = ''

        # Futures tracking steps in the connection's lifecycle.
        # Set to True when the opening handshake has completed properly.
        self.opening_handshake = asyncio.Future(loop=loop)
        # Set to True when the closing handshake has completed properly and to
        # False when the connection terminates abnormally.
        self.closing_handshake = asyncio.Future(loop=loop)
        # Set to None when the connection state becomes CLOSED.
        self.connection_closed = asyncio.Future(loop=loop)

        # Queue of received messages.
        self.messages = asyncio.queues.Queue(max_queue, loop=loop)

        # Mapping of ping IDs to waiters, in chronological order.
        self.pings = collections.OrderedDict()

        # Task managing the connection, initalized in self.client_connected.
        self.worker_task = None

        # In a subclass implementing the opening handshake, the state will be
        # CONNECTING at this point.
        if self.state == OPEN:
            self.opening_handshake.set_result(True)

    # Public API

    @property
    def local_address(self):
        """
        Local address of the connection.

        This is a ``(host, port)`` tuple or ``None`` if the connection hasn't
        been established yet.

        """
        if self.writer is None:
            return None
        return self.writer.get_extra_info('sockname')

    @property
    def remote_address(self):
        """
        Remote address of the connection.

        This is a ``(host, port)`` tuple or ``None`` if the connection hasn't
        been established yet.

        """
        if self.writer is None:
            return None
        return self.writer.get_extra_info('peername')

    @property
    def open(self):
        """
        This property is ``True`` when the connection is usable.

        It may be used to detect disconnections but this is discouraged per
        the EAFP_ principle. When ``open`` is ``False``, using the connection
        raises a :exc:`~websockets.exceptions.ConnectionClosed` exception.

        .. _EAFP: https://docs.python.org/3/glossary.html#term-eafp

        """
        return self.state == OPEN

    @property
    def state_name(self):
        """
        Current connection state, as a string.

        Possible states are defined in the WebSocket specification:
        CONNECTING, OPEN, CLOSING, or CLOSED.

        To check if the connection is open, use :attr:`open` instead.

        """
        return ['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'][self.state]

    @asyncio.coroutine
    def close(self, code=1000, reason=''):
        """
        This coroutine performs the closing handshake.

        It waits for the other end to complete the handshake. It doesn't do
        anything once the connection is closed. Thus it's idemptotent.

        It's safe to wrap this coroutine in :func:`~asyncio.ensure_future`
        since errors during connection termination aren't particularly useful.

        ``code`` must be an :class:`int` and ``reason`` a :class:`str`.

        """
        if self.state == OPEN:
            # 7.1.2. Start the WebSocket Closing Handshake
            # 7.1.3. The WebSocket Closing Handshake is Started
            frame_data = serialize_close(code, reason)
            yield from self.write_frame(OP_CLOSE, frame_data)

        # If the connection doesn't terminate within the timeout, break out of
        # the worker loop.
        try:
            yield from asyncio.wait_for(
                self.worker_task, self.timeout, loop=self.loop)
        except asyncio.TimeoutError:
            self.worker_task.cancel()

        # The worker should terminate quickly once it has been cancelled.
        yield from self.worker_task

    @asyncio.coroutine
    def recv(self):
        """
        This coroutine receives the next message.

        It returns a :class:`str` for a text frame and :class:`bytes` for a
        binary frame.

        When the end of the message stream is reached, :meth:`recv` raises
        :exc:`~websockets.exceptions.ConnectionClosed`. This can happen after
        a normal connection closure, a protocol error or a network failure.

        .. versionchanged:: 3.0

            :meth:`recv` used to return ``None`` instead. Refer to the
            changelog for details.

        """
        # Don't yield from self.ensure_open() here because messages could be
        # available in the queue even if the connection is closed.

        # Return any available message
        try:
            return self.messages.get_nowait()
        except asyncio.queues.QueueEmpty:
            pass

        # Don't yield from self.ensure_open() here because messages could be
        # received before the closing frame even if the connection is closing.

        # Wait for a message until the connection is closed
        next_message = asyncio_ensure_future(
            self.messages.get(), loop=self.loop)
        try:
            done, pending = yield from asyncio.wait(
                [next_message, self.worker_task],
                loop=self.loop, return_when=asyncio.FIRST_COMPLETED)
        except asyncio.CancelledError:
            # Handle the Task.cancel()
            next_message.cancel()
            raise

        # Now there's no need to yield from self.ensure_open(). Either a
        # message was received or the connection was closed.

        if next_message in done:
            return next_message.result()
        else:
            next_message.cancel()
            if not self.legacy_recv:
                raise ConnectionClosed(self.close_code, self.close_reason)

    @asyncio.coroutine
    def send(self, data):
        """
        This coroutine sends a message.

        It sends :class:`str` as a text frame and :class:`bytes` as a binary
        frame. It raises a :exc:`TypeError` for other inputs.

        """
        yield from self.ensure_open()

        if isinstance(data, str):
            opcode = 1
            data = data.encode('utf-8')
        elif isinstance(data, bytes):
            opcode = 2
        else:
            raise TypeError("data must be bytes or str")

        yield from self.write_frame(opcode, data)

    @asyncio.coroutine
    def ping(self, data=None):
        """
        This coroutine sends a ping.

        It returns a :class:`~asyncio.Future` which will be completed when the
        corresponding pong is received and which you may ignore if you don't
        want to wait.

        A ping may serve as a keepalive or as a check that the remote endpoint
        received all messages up to this point, with ``yield from ws.ping()``.

        By default, the ping contains four random bytes. The content may be
        overridden with the optional ``data`` argument which must be of type
        :class:`str` (which will be encoded to UTF-8) or :class:`bytes`.

        """
        yield from self.ensure_open()

        if data is not None:
            data = self.encode_data(data)

        # Protect against duplicates if a payload is explicitly set.
        if data in self.pings:
            raise ValueError("Already waiting for a pong with the same data")

        # Generate a unique random payload otherwise.
        while data is None or data in self.pings:
            data = struct.pack('!I', random.getrandbits(32))

        self.pings[data] = asyncio.Future(loop=self.loop)
        yield from self.write_frame(OP_PING, data)
        return self.pings[data]

    @asyncio.coroutine
    def pong(self, data=b''):
        """
        This coroutine sends a pong.

        An unsolicited pong may serve as a unidirectional heartbeat.

        The content may be overridden with the optional ``data`` argument
        which must be of type :class:`str` (which will be encoded to UTF-8) or
        :class:`bytes`.

        """
        yield from self.ensure_open()

        data = self.encode_data(data)

        yield from self.write_frame(OP_PONG, data)

    # Private methods - no guarantees.

    def encode_data(self, data):
        # Expect str or bytes, return bytes.
        if isinstance(data, str):
            return data.encode('utf-8')
        elif isinstance(data, bytes):
            return data
        else:
            raise TypeError("data must be bytes or str")

    @asyncio.coroutine
    def ensure_open(self):
        # Raise a suitable exception if the connection isn't open.
        # Handle cases from the most common to the least common.

        if self.state == OPEN:
            return

        if self.state == CLOSED:
            raise ConnectionClosed(self.close_code, self.close_reason)

        # If the closing handshake is in progress, let it complete to get the
        # proper close status and code. As an safety measure, the timeout is
        # longer than the worst case (2 * self.timeout) but not unlimited.
        if self.state == CLOSING:
            yield from asyncio.wait_for(
                self.worker_task, 3 * self.timeout, loop=self.loop)
            raise ConnectionClosed(self.close_code, self.close_reason)

        # Control may only reach this point in buggy third-party subclasses.
        assert self.state == CONNECTING
        raise InvalidState("WebSocket connection isn't established yet.")

    @asyncio.coroutine
    def run(self):
        # This coroutine guarantees that the connection is closed at exit.
        yield from self.opening_handshake
        while not self.closing_handshake.done():
            try:
                msg = yield from self.read_message()
                if msg is None:
                    break
                yield from self.messages.put(msg)
            except asyncio.CancelledError:
                break
            except WebSocketProtocolError:
                yield from self.fail_connection(1002)
            except asyncio.IncompleteReadError:
                yield from self.fail_connection(1006)
            except UnicodeDecodeError:
                yield from self.fail_connection(1007)
            except PayloadTooBig:
                yield from self.fail_connection(1009)
            except Exception:
                yield from self.fail_connection(1011)
                raise
        yield from self.close_connection()

    @asyncio.coroutine
    def read_message(self):
        # Reassemble fragmented messages.
        frame = yield from self.read_data_frame(max_size=self.max_size)
        if frame is None:
            return
        if frame.opcode == OP_TEXT:
            text = True
        elif frame.opcode == OP_BINARY:
            text = False
        else:   # frame.opcode == OP_CONT
            raise WebSocketProtocolError("Unexpected opcode")

        # Shortcut for the common case - no fragmentation
        if frame.fin:
            return frame.data.decode('utf-8') if text else frame.data

        # 5.4. Fragmentation
        chunks = []
        max_size = self.max_size
        if text:
            decoder = codecs.getincrementaldecoder('utf-8')(errors='strict')
            if max_size is None:
                def append(frame):
                    nonlocal chunks
                    chunks.append(decoder.decode(frame.data, frame.fin))
            else:
                def append(frame):
                    nonlocal chunks, max_size
                    chunks.append(decoder.decode(frame.data, frame.fin))
                    max_size -= len(frame.data)
        else:
            if max_size is None:
                def append(frame):
                    nonlocal chunks
                    chunks.append(frame.data)
            else:
                def append(frame):
                    nonlocal chunks, max_size
                    chunks.append(frame.data)
                    max_size -= len(frame.data)
        append(frame)

        while not frame.fin:
            frame = yield from self.read_data_frame(max_size=max_size)
            if frame is None:
                raise WebSocketProtocolError("Incomplete fragmented message")
            if frame.opcode != OP_CONT:
                raise WebSocketProtocolError("Unexpected opcode")
            append(frame)

        return ('' if text else b'').join(chunks)

    @asyncio.coroutine
    def read_data_frame(self, max_size):
        # Deal with control frames automatically and return next data frame.
        # 6.2. Receiving Data
        while True:
            frame = yield from self.read_frame(max_size)

            # 5.5. Control Frames
            if frame.opcode == OP_CLOSE:
                # Make sure the close frame is valid before echoing it.
                code, reason = parse_close(frame.data)
                if self.state == OPEN:
                    # 7.1.3. The WebSocket Closing Handshake is Started
                    yield from self.write_frame(OP_CLOSE, frame.data)
                self.close_code, self.close_reason = code, reason
                self.closing_handshake.set_result(True)
                return

            elif frame.opcode == OP_PING:
                # Answer pings.
                yield from self.pong(frame.data)

            elif frame.opcode == OP_PONG:
                # Do not acknowledge pings on unsolicited pongs.
                if frame.data in self.pings:
                    # Acknowledge all pings up to the one matching this pong.
                    ping_id = None
                    while ping_id != frame.data:
                        ping_id, waiter = self.pings.popitem(0)
                        if not waiter.cancelled():
                            waiter.set_result(None)

            # 5.6. Data Frames
            else:
                return frame

    @asyncio.coroutine
    def read_frame(self, max_size):
        is_masked = not self.is_client
        frame = yield from read_frame(
            self.reader.readexactly, is_masked, max_size=max_size)
        side = 'client' if self.is_client else 'server'
        logger.debug("%s << %s", side, frame)
        return frame

    @asyncio.coroutine
    def write_frame(self, opcode, data=b''):
        # Defensive assertion for protocol compliance.
        if self.state != OPEN:                              # pragma: no cover
            raise InvalidState("Cannot write to a WebSocket "
                               "in the {} state".format(self.state_name))

        # Make sure no other frame will be sent after a close frame. Do this
        # before yielding control to avoid sending more than one close frame.
        if opcode == OP_CLOSE:
            self.state = CLOSING
        frame = Frame(True, opcode, data)
        side = 'client' if self.is_client else 'server'
        logger.debug("%s >> %s", side, frame)
        is_masked = self.is_client
        write_frame(frame, self.writer.write, is_masked)

        # Backport of the combined logic of:
        # https://github.com/python/asyncio/pull/280
        # https://github.com/python/asyncio/pull/291
        # Remove when dropping support for Python < 3.6.
        transport = self.writer._transport
        if transport is not None:                           # pragma: no cover
            # PR 291 added the is_closing method to transports shortly after
            # PR 280 fixed the bug we're trying to work around in this block.
            if not hasattr(transport, 'is_closing'):
                # This emulates what is_closing would return if it existed.
                try:
                    is_closing = transport._closing
                except AttributeError:
                    is_closing = transport._closed
                if is_closing:
                    yield

        try:
            # drain() cannot be called concurrently by multiple coroutines:
            # http://bugs.python.org/issue29930. Remove this lock when no
            # version of Python where this bugs exists is supported anymore.
            with (yield from self._drain_lock):
                # Handle flow control automatically.
                yield from self.writer.drain()
        except ConnectionError:
            # Terminate the connection if the socket died.
            yield from self.fail_connection(1006)
            # And raise an exception, since the frame couldn't be sent.
            raise ConnectionClosed(self.close_code, self.close_reason)

    @asyncio.coroutine
    def close_connection(self, force=False):
        # 7.1.1. Close the WebSocket Connection
        if self.state == CLOSED:
            return

        # Defensive assertion for protocol compliance.
        if self.state != CLOSING and not force:             # pragma: no cover
            raise InvalidState("Cannot close a WebSocket connection "
                               "in the {} state".format(self.state_name))

        if self.is_client and not force:
            try:
                yield from asyncio.wait_for(
                    self.connection_closed, self.timeout, loop=self.loop)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

            if self.state == CLOSED:
                return

        # Attempt to terminate the TCP connection properly.
        # If the socket is already closed, this may crash.
        try:
            if self.writer.can_write_eof():
                self.writer.write_eof()
        except Exception:                                   # pragma: no cover
            pass

        self.writer.close()

        try:
            yield from asyncio.wait_for(
                self.connection_closed, self.timeout, loop=self.loop)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    @asyncio.coroutine
    def fail_connection(self, code=1011, reason=''):
        # 7.1.7. Fail the WebSocket Connection
        logger.info("Failing the WebSocket connection: %d %s", code, reason)
        if self.state == OPEN:
            if code == 1006:
                # Don't send a close frame if the connection is broken. Set
                # the state to CLOSING to allow close_connection to proceed.
                self.state = CLOSING
            else:
                frame_data = serialize_close(code, reason)
                yield from self.write_frame(OP_CLOSE, frame_data)
        if not self.closing_handshake.done():
            self.close_code, self.close_reason = code, reason
            self.closing_handshake.set_result(False)
        yield from self.close_connection()

    # asyncio StreamReaderProtocol methods

    def client_connected(self, reader, writer):
        self.reader = reader
        self.writer = writer
        # Configure write buffer limit.
        self.writer._transport.set_write_buffer_limits(self.write_limit)
        # Start the task that handles incoming messages.
        self.worker_task = asyncio_ensure_future(self.run(), loop=self.loop)

    def eof_received(self):
        super().eof_received()
        # Since Python 3.5, StreamReaderProtocol.eof_received() returns True
        # to leave the transport open (http://bugs.python.org/issue24539).
        # This is inappropriate for websockets for at least three reasons.
        # 1. The use case is to read data until EOF with self.reader.read(-1).
        #    Since websockets is a TLV protocol, this never happens.
        # 2. It doesn't work on SSL connections. A falsy value must be
        #    returned to have the same behavior on SSL and plain connections.
        # 3. The websockets protocol has its own closing handshake. Endpoints
        #    close the TCP connection after sending a Close frame.
        # As a consequence we revert to the previous, more useful behavior.
        return

    def connection_lost(self, exc):
        # 7.1.4. The WebSocket Connection is Closed
        self.state = CLOSED
        if not self.opening_handshake.done():
            self.opening_handshake.set_result(False)
        if not self.closing_handshake.done():
            self.close_code, self.close_reason = 1006, ''
            self.closing_handshake.set_result(False)
        if not self.connection_closed.done():
            self.connection_closed.set_result(None)
        # Close the transport in case close_connection() wasn't executed.
        if self.writer is not None:
            self.writer.close()
        super().connection_lost(exc)
