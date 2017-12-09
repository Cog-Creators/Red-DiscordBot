"""
The :mod:`websockets.framing` module implements data framing as specified in
`section 5 of RFC 6455`_.

It deals with a single frame at a time. Anything that depends on the sequence
of frames is implemented in :mod:`websockets.protocol`.

.. _section 5 of RFC 6455: http://tools.ietf.org/html/rfc6455#section-5

"""

import asyncio
import collections
import io
import random
import struct

from .exceptions import PayloadTooBig, WebSocketProtocolError


try:
    from .speedups import apply_mask
except ImportError:                                         # pragma: no cover
    from .utils import apply_mask


__all__ = [
    'OP_CONT', 'OP_TEXT', 'OP_BINARY', 'OP_CLOSE', 'OP_PING', 'OP_PONG',
    'Frame', 'read_frame', 'write_frame', 'parse_close', 'serialize_close'
]

OP_CONT, OP_TEXT, OP_BINARY = range(0x00, 0x03)
OP_CLOSE, OP_PING, OP_PONG = range(0x08, 0x0b)

CLOSE_CODES = {
    1000: "OK",
    1001: "going away",
    1002: "protocol error",
    1003: "unsupported type",
    # 1004: - (reserved)
    # 1005: no status code (internal)
    # 1006: connection closed abnormally (internal)
    1007: "invalid data",
    1008: "policy violation",
    1009: "message too big",
    1010: "extension required",
    1011: "unexpected error",
    # 1015: TLS failure (internal)
}


Frame = collections.namedtuple('Frame', ('fin', 'opcode', 'data'))
Frame.__doc__ = """WebSocket frame.

* ``fin`` is the FIN bit
* ``opcode`` is the opcode
* ``data`` is the payload data

Only these three fields are needed by higher level code. The MASK bit, payload
length and masking-key are handled on the fly by :func:`read_frame` and
:func:`write_frame`.

"""


@asyncio.coroutine
def read_frame(reader, mask, *, max_size=None):
    """
    Read a WebSocket frame and return a :class:`Frame` object.

    ``reader`` is a coroutine taking an integer argument and reading exactly
    this number of bytes, unless the end of file is reached.

    ``mask`` is a :class:`bool` telling whether the frame should be masked
    i.e. whether the read happens on the server side.

    If ``max_size`` is set and the payload exceeds this size in bytes,
    :exc:`~websockets.exceptions.PayloadTooBig` is raised.

    This function validates the frame before returning it and raises
    :exc:`~websockets.exceptions.WebSocketProtocolError` if it contains
    incorrect values.

    """
    # Read the header
    data = yield from reader(2)
    head1, head2 = struct.unpack('!BB', data)
    fin = bool(head1 & 0b10000000)
    if head1 & 0b01110000:
        raise WebSocketProtocolError("Reserved bits must be 0")
    opcode = head1 & 0b00001111
    if bool(head2 & 0b10000000) != mask:
        raise WebSocketProtocolError("Incorrect masking")
    length = head2 & 0b01111111
    if length == 126:
        data = yield from reader(2)
        length, = struct.unpack('!H', data)
    elif length == 127:
        data = yield from reader(8)
        length, = struct.unpack('!Q', data)
    if max_size is not None and length > max_size:
        raise PayloadTooBig("Payload exceeds limit "
                            "({} > {} bytes)".format(length, max_size))
    if mask:
        mask_bits = yield from reader(4)

    # Read the data
    data = yield from reader(length)
    if mask:
        data = apply_mask(data, mask_bits)

    frame = Frame(fin, opcode, data)
    check_frame(frame)
    return frame


def write_frame(frame, writer, mask):
    """
    Write a WebSocket frame.

    ``frame`` is the :class:`Frame` object to write.

    ``writer`` is a function accepting bytes.

    ``mask`` is a :class:`bool` telling whether the frame should be masked
    i.e. whether the write happens on the client side.

    This function validates the frame before sending it and raises
    :exc:`~websockets.exceptions.WebSocketProtocolError` if it contains
    incorrect values.

    """
    check_frame(frame)
    output = io.BytesIO()

    # Prepare the header
    head1 = 0b10000000 if frame.fin else 0
    head1 |= frame.opcode
    head2 = 0b10000000 if mask else 0
    length = len(frame.data)
    if length < 0x7e:
        output.write(struct.pack('!BB', head1, head2 | length))
    elif length < 0x10000:
        output.write(struct.pack('!BBH', head1, head2 | 126, length))
    else:
        output.write(struct.pack('!BBQ', head1, head2 | 127, length))
    if mask:
        mask_bits = struct.pack('!I', random.getrandbits(32))
        output.write(mask_bits)

    # Prepare the data
    if mask:
        data = apply_mask(frame.data, mask_bits)
    else:
        data = frame.data
    output.write(data)

    # Send the frame
    writer(output.getvalue())


def check_frame(frame):
    """
    Raise :exc:`~websockets.exceptions.WebSocketProtocolError` if the frame
    contains incorrect values.

    """
    if frame.opcode in (OP_CONT, OP_TEXT, OP_BINARY):
        return
    elif frame.opcode in (OP_CLOSE, OP_PING, OP_PONG):
        if len(frame.data) > 125:
            raise WebSocketProtocolError("Control frame too long")
        if not frame.fin:
            raise WebSocketProtocolError("Fragmented control frame")
    else:
        raise WebSocketProtocolError("Invalid opcode")


def parse_close(data):
    """
    Parse the data in a close frame.

    Return ``(code, reason)`` when ``code`` is an :class:`int` and ``reason``
    a :class:`str`.

    Raise :exc:`~websockets.exceptions.WebSocketProtocolError` or
    :exc:`UnicodeDecodeError` if the data is invalid.

    """
    length = len(data)
    if length == 0:
        return 1005, ''
    elif length == 1:
        raise WebSocketProtocolError("Close frame too short")
    else:
        code, = struct.unpack('!H', data[:2])
        if not (code in CLOSE_CODES or 3000 <= code < 5000):
            raise WebSocketProtocolError("Invalid status code")
        reason = data[2:].decode('utf-8')
        return code, reason


def serialize_close(code, reason):
    """
    Serialize the data for a close frame.

    This is the reverse of :func:`parse_close`.

    """
    return struct.pack('!H', code) + reason.encode('utf-8')
