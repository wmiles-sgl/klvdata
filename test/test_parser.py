#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2017 Matthew Pare (paretech@gmail.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE

import unittest


class ParserTestCase(unittest.TestCase):
    pass


class ParserSingleShort(ParserTestCase):
    def setUp(self):
        self.key = b'\x02'
        self.length = b'\x08'
        self.value = b'\x00\x04\x60\x50\x58\x4E\x01\x80'

        self.packet = self.key + self.length + self.value

        from klvdata.klvparser import KLVParser
        self.parser = KLVParser(self.packet, key_length=1)

    def test_key(self):
        key, value = next(self.parser)
        self.assertEqual(key, self.key)

    def test_value(self):
        key, value = next(self.parser)
        self.assertEqual(value, self.value)


class ParserSingleLong(ParserTestCase):
    def setUp(self):
        self.packet = bytes()

        # Sample data from MISB ST 0902.5
        with open('./data/DynamicConstantMISMMSPacketData.bin', 'rb') as f:
            self.packet = f.read()

        self.key = self.packet[0:16]
        assert len(self.key) == 16
        self.length = self.packet[16:18]
        assert len(self.length) == 2
        self.value = self.packet[18:]

        from klvdata.klvparser import KLVParser
        self.parser = KLVParser(self.packet, key_length=16)

    def test_key(self):
        key, value = next(self.parser)
        self.assertEqual(key, self.key)

    def test_value(self):
        key, value = next(self.parser)
        self.assertEqual(value, self.value)


class TagParserTestCase(unittest.TestCase):
    def _make_parser(self, packet):
        from klvdata.tagparser import TagParser
        return TagParser(packet)

    def _tlv(self, encoded_tag, value):
        return encoded_tag + bytes([len(value)]) + value

    def test_single_byte_tag(self):
        # Tags < 128 are a single byte; decoded integer equals the byte value.
        value = b'\x00\x04\x60\x50\x58\x4E\x01\x80'
        packet = self._tlv(b'\x02', value)
        tag, parsed_value = next(self._make_parser(packet))
        self.assertEqual(tag, 2)
        self.assertEqual(parsed_value, value)

    def test_two_byte_tag_128(self):
        # Tag 128: BER-OID wire encoding is 0x81 0x00.
        value = b'\xAB\xCD'
        packet = self._tlv(b'\x81\x00', value)
        tag, parsed_value = next(self._make_parser(packet))
        self.assertEqual(tag, 128)
        self.assertEqual(parsed_value, value)

    def test_two_byte_tag_255(self):
        # Tag 255: BER-OID wire encoding is 0x81 0x7F.
        value = b'\x01\x02\x03'
        packet = self._tlv(b'\x81\x7F', value)
        tag, parsed_value = next(self._make_parser(packet))
        self.assertEqual(tag, 255)
        self.assertEqual(parsed_value, value)

    def test_three_byte_tag_16384(self):
        # Tag 16384 = 0x4000: BER-OID wire encoding is 0x81 0x80 0x00.
        value = b'\xDE\xAD'
        packet = self._tlv(b'\x81\x80\x00', value)
        tag, parsed_value = next(self._make_parser(packet))
        self.assertEqual(tag, 16384)
        self.assertEqual(parsed_value, value)

    def test_multiple_elements(self):
        # Two consecutive BER-OID elements in one stream.
        value1 = b'\xAA'
        value2 = b'\xBB\xCC'
        packet = self._tlv(b'\x02', value1) + self._tlv(b'\x81\x00', value2)
        parser = self._make_parser(packet)
        tag1, v1 = next(parser)
        tag2, v2 = next(parser)
        self.assertEqual(tag1, 2)
        self.assertEqual(v1, value1)
        self.assertEqual(tag2, 128)
        self.assertEqual(v2, value2)

    def test_exhausted_raises_stop_iteration(self):
        packet = self._tlv(b'\x01', b'\xFF')
        parser = self._make_parser(packet)
        next(parser)
        with self.assertRaises(StopIteration):
            next(parser)


if __name__ == "__main__":
    unittest.main()
