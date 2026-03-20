#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2026 Will Miles (wmiles@sgl.com)
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
# SOFTWARE.

from io import BytesIO
from io import IOBase


class TagParser:
    """Yield (tag: int, value: bytes) from a BER-OID TLV byte stream.

    Each tag is decoded from BER-OID encoding: each byte contributes 7
    value bits (bits 6-0); bit 7 is the continuation flag (1 = more bytes
    follow, 0 = last byte). The 7-bit groups are concatenated MSB-first to
    form the integer tag number. This matches the encoding used for MISB ST
    0601 Local Set tags >= 128.
    """

    def __init__(self, source):
        if isinstance(source, IOBase):
            self.source = source
        else:
            self.source = BytesIO(source)

    def __iter__(self):
        return self

    def __next__(self):
        tag = self._read_tag()

        byte_length = self.__read(1)[0]

        if byte_length < 128:
            # BER Short Form
            length = byte_length
        else:
            # BER Long Form
            length = int.from_bytes(self.__read(byte_length - 128), 'big')

        value = self.__read(length)

        return tag, value

    def _read_tag(self):
        """Decode a BER-OID encoded tag and return it as an integer."""
        value = 0
        while True:
            byte = self.__read(1)
            value = (value << 7) | (byte[0] & 0x7F)
            if not (byte[0] & 0x80):
                return value

    def __read(self, size):
        if size == 0:
            return b''

        data = self.source.read(size)

        if data:
            return data

        raise StopIteration
