import asyncio
import unittest
import unittest.mock

from .exceptions import PayloadTooBig, WebSocketProtocolError
from .framing import *


class FramingTests(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def decode(self, message, mask=False, max_size=None):
        self.stream = asyncio.StreamReader(loop=self.loop)
        self.stream.feed_data(message)
        self.stream.feed_eof()
        frame = self.loop.run_until_complete(read_frame(
            self.stream.readexactly, mask, max_size=max_size))
        # Make sure all the data was consumed.
        self.assertTrue(self.stream.at_eof())
        return frame

    def encode(self, frame, mask=False):
        writer = unittest.mock.Mock()
        write_frame(frame, writer, mask)
        # Ensure the entire frame is sent with a single call to writer().
        # Multiple calls cause TCP fragmentation and degrade performance.
        self.assertEqual(writer.call_count, 1)
        # The frame data is the single positional argument of that call.
        return writer.call_args[0][0]

    def round_trip(self, message, expected, mask=False):
        decoded = self.decode(message, mask)
        self.assertEqual(decoded, expected)
        encoded = self.encode(decoded, mask)
        if mask:    # non-deterministic encoding
            decoded = self.decode(encoded, mask)
            self.assertEqual(decoded, expected)
        else:       # deterministic encoding
            self.assertEqual(encoded, message)

    def round_trip_close(self, data, code, reason):
        parsed = parse_close(data)
        self.assertEqual(parsed, (code, reason))
        serialized = serialize_close(code, reason)
        self.assertEqual(serialized, data)

    def test_text(self):
        self.round_trip(b'\x81\x04Spam', Frame(True, OP_TEXT, b'Spam'))

    def test_text_masked(self):
        self.round_trip(
            b'\x81\x84\x5b\xfb\xe1\xa8\x08\x8b\x80\xc5',
            Frame(True, OP_TEXT, b'Spam'), mask=True)

    def test_binary(self):
        self.round_trip(b'\x82\x04Eggs', Frame(True, OP_BINARY, b'Eggs'))

    def test_binary_masked(self):
        self.round_trip(
            b'\x82\x84\x53\xcd\xe2\x89\x16\xaa\x85\xfa',
            Frame(True, OP_BINARY, b'Eggs'), mask=True)

    def test_non_ascii_text(self):
        self.round_trip(
            b'\x81\x05caf\xc3\xa9',
            Frame(True, OP_TEXT, 'café'.encode('utf-8')))

    def test_non_ascii_text_masked(self):
        self.round_trip(
            b'\x81\x85\x64\xbe\xee\x7e\x07\xdf\x88\xbd\xcd',
            Frame(True, OP_TEXT, 'café'.encode('utf-8')), mask=True)

    def test_close(self):
        self.round_trip(b'\x88\x00', Frame(True, OP_CLOSE, b''))

    def test_ping(self):
        self.round_trip(b'\x89\x04ping', Frame(True, OP_PING, b'ping'))

    def test_pong(self):
        self.round_trip(b'\x8a\x04pong', Frame(True, OP_PONG, b'pong'))

    def test_long(self):
        self.round_trip(
            b'\x82\x7e\x00\x7e' + 126 * b'a',
            Frame(True, OP_BINARY, 126 * b'a'))

    def test_very_long(self):
        self.round_trip(
            b'\x82\x7f\x00\x00\x00\x00\x00\x01\x00\x00' + 65536 * b'a',
            Frame(True, OP_BINARY, 65536 * b'a'))

    def test_payload_too_big(self):
        with self.assertRaises(PayloadTooBig):
            self.decode(b'\x82\x7e\x04\x01' + 1025 * b'a', max_size=1024)

    def test_bad_reserved_bits(self):
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\xc0\x00')
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\xa0\x00')
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\x90\x00')

    def test_bad_opcode(self):
        for opcode in list(range(0x00, 0x03)) + list(range(0x08, 0x0b)):
            self.decode(bytes([0x80 | opcode, 0]))
        for opcode in list(range(0x03, 0x08)) + list(range(0x0b, 0x10)):
            with self.assertRaises(WebSocketProtocolError):
                self.decode(bytes([0x80 | opcode, 0]))

    def test_bad_mask_flag(self):
        self.decode(b'\x80\x80\x00\x00\x00\x00', mask=True)
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\x80\x80\x00\x00\x00\x00')
        self.decode(b'\x80\x00')
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\x80\x00', mask=True)

    def test_control_frame_too_long(self):
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\x88\x7e\x00\x7e' + 126 * b'a')

    def test_fragmented_control_frame(self):
        with self.assertRaises(WebSocketProtocolError):
            self.decode(b'\x08\x00')

    def test_parse_close(self):
        self.round_trip_close(b'\x03\xe8', 1000, '')
        self.round_trip_close(b'\x03\xe8OK', 1000, 'OK')

    def test_parse_close_empty(self):
        self.assertEqual(parse_close(b''), (1005, ''))

    def test_parse_close_errors(self):
        with self.assertRaises(WebSocketProtocolError):
            parse_close(b'\x03')
        with self.assertRaises(WebSocketProtocolError):
            parse_close(b'\x03\xe7')
        with self.assertRaises(UnicodeDecodeError):
            parse_close(b'\x03\xe8\xff\xff')
