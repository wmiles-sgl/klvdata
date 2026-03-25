#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
# SOFTWARE.

from abc import ABCMeta
from abc import abstractmethod
from typing import ClassVar
from klvdata.element import Element
from klvdata.common import bytes_to_datetime
from klvdata.common import bytes_to_int
from klvdata.common import bytes_to_float
from klvdata.common import bytes_to_hexstr
from klvdata.common import bytes_to_str
from klvdata.common import datetime_to_bytes
from klvdata.common import float_to_bytes
from klvdata.common import imapb_forward
from klvdata.common import imapb_reverse
from klvdata.common import str_to_bytes
from klvdata.common import ieee754_bytes_to_fp
from klvdata.common import ieee754_fp_to_bytes
                                           


class ElementParser(Element, metaclass=ABCMeta):
    """Construct a Element Parser base class.

    Element Parsers are used to enforce the convention that all Element Parsers
    already know the key of the element they are constructing.

    Element Parser is a helper class that simplifies known element definition
    and makes a layer of abstraction for functionality that all known elements
    can share. The parsing interfaces are cleaner and require less coding as
    their definitions (subclasses of Element Parser) do not need to call init
    on super with class key and instance value.
    """

    key: ClassVar[bytes]

    def __init__(self, value):
        super().__init__(self.key, value)

    def __repr__(self):
        """Return as-code string used to re-create the object."""
        return '{}({})'.format(self.name, bytes(self.value))


class BaseValue(metaclass=ABCMeta):
    """Abstract base class (superclass) used to insure internal interfaces are maintained."""
    @abstractmethod
    def __bytes__(self) -> bytes:
        """Required by element.Element"""
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Required by element.Element"""
        pass


class BytesElementParser(ElementParser, metaclass=ABCMeta):
    def __init__(self, value):
        super().__init__(BytesValue(value))


class BytesValue(BaseValue):
    def __init__(self, value):
        self.value = value

    def __bytes__(self):
        return bytes(self.value)

    def __str__(self):
        return bytes_to_hexstr(self.value, start='0x', sep='')


class DateTimeElementParser(ElementParser, metaclass=ABCMeta):
    def __init__(self, value):
        super().__init__(DateTimeValue(value))


class DateTimeValue(BaseValue):
    def __init__(self, value):
        self.value = bytes_to_datetime(value)

    def __bytes__(self):
        return datetime_to_bytes(self.value)

    def __str__(self):
        return self.value.isoformat(sep=' ')


class StringElementParser(ElementParser, metaclass=ABCMeta):
    def __init__(self, value):
        super().__init__(StringValue(value))


class StringValue(BaseValue):
    def __init__(self, value):
        try:
            self.value = bytes_to_str(value)
        except TypeError:
            self.value = value

    def __bytes__(self):
        return str_to_bytes(self.value)

    def __str__(self):
        if self.value is not None:
            return str(self.value)
        return ""


class MappedElementParser(ElementParser, metaclass=ABCMeta):
    _domain: ClassVar[tuple]
    _range: ClassVar[tuple]
    _error: ClassVar

    def __init__(self, value):
        super().__init__(MappedValue(value, self._domain, self._range, self._error))

class MappedValue(BaseValue):
    def __init__(self, value, _domain, _range, _error):
        self._domain = _domain
        self._range = _range
        self._error = _error

        try:
            self.value = bytes_to_float(value, self._domain, self._range, self._error)
        except TypeError:
            self.value = value

    def __bytes__(self):
        return float_to_bytes(self.value, self._domain, self._range, self._error)

    def __str__(self):
        if self.value is not None:
            return format(self.value)
        return ""

    def __float__(self):
        return self.value

class IMAPBElementParser(ElementParser, metaclass=ABCMeta):
    """Parser for IMAPB variable-length floating-point mapped items (ST 1201).

    Subclasses declare:
        _range   = (a, b)   – physical min/max
        _length  = N        – default encoding byte count (used when encoding
                              from a float; decoding always uses actual byte count)
    """
    _range: ClassVar[tuple]
    _length: ClassVar[int] = 2

    def __init__(self, value):
        super().__init__(IMAPBValue(value, self._range, self._length))


class IMAPBValue(BaseValue):
    def __init__(self, value, _range, _default_length=2):
        self._range = _range
        self._enc_length = _default_length
        try:
            raw = bytes(value)
            if raw:
                self._enc_length = len(raw)
                self.value = imapb_reverse(raw, _range[0], _range[1])
            else:
                self.value = None
        except TypeError:
            # Constructed from a Python numeric value rather than bytes
            self.value = float(value) if value is not None else None

    def __bytes__(self):
        return imapb_forward(self.value, self._range[0], self._range[1], self._enc_length)

    def __str__(self):
        if self.value is not None:
            return format(self.value)
        return ""

    def __float__(self) -> float:
        if self.value is None:
            raise TypeError("Cannot convert None to float")
        return float(self.value)


class IntegerElementParser(ElementParser, metaclass=ABCMeta):
    """Parser for big-endian integer items.

    Subclasses may set:
        _signed = True   – for signed integers (default False)
        _length = N      – to fix serialization to exactly N bytes (default None = minimum bytes needed)
    """
    _signed = False
    _length = None

    def __init__(self, value):
        super().__init__(IntegerValue(value, self._signed, self._length))


class IntegerValue(BaseValue):
    def __init__(self, value, signed=False, length=None):
        self._signed = signed
        self._length = length
        if isinstance(value, int):
            self.value = value
        else:
            try:
                self.value = bytes_to_int(bytes(value), signed=signed)
            except TypeError:
                self.value = int(value) if value is not None else None

    def __bytes__(self):
        if self.value is None:
            return b'\x00'
        if self._length is not None:
            length = self._length
        elif self._signed:
            length = max(1, (self.value.bit_length() + 8) // 8)
        else:
            length = max(1, (self.value.bit_length() + 7) // 8)
        return self.value.to_bytes(length, byteorder='big', signed=self._signed)

    def __str__(self):
        if self.value is not None:
            return str(self.value)
        return ""

    def __int__(self):
        return self.value


class IEEE754ElementParser(ElementParser, metaclass=ABCMeta):
    def __init__(self, value):
        super().__init__(IEEE754Value(value))


class IEEE754Value(BaseValue):
    def __init__(self, value, length=None):
        self._length = length
        try:
            self.value = ieee754_bytes_to_fp(value)
        except TypeError:
            self.value = value

    def __bytes__(self):
        if self._length is not None:
            length = self._length
        else:
            length = 8  # Double precision
        return ieee754_fp_to_bytes(self.value, length)

    def __str__(self):
        return bytes_to_hexstr(self.value, start='0x', sep='')



