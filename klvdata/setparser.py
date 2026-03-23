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

from pprint import pformat
from abc import ABCMeta
from abc import abstractmethod
from collections import OrderedDict
from typing import ClassVar
from klvdata.element import Element
from klvdata.element import UnknownElement
from klvdata.klvparser import KLVParser
from klvdata.tagparser import TagParser


class SetParser(Element, metaclass=ABCMeta):
    """Parsable Element. Not intended to be used directly. Always as super class."""
    _unknown_element = UnknownElement
    _parser_class = KLVParser

    def __init__(self, value, key_length=1):
        """All parser needs is the value, no other information"""
        super().__init__(self.key, value)
        if not hasattr(self, 'key_length'):
            self.key_length = key_length
        self.items = OrderedDict()
        self.parse()

    def __getitem__(self, key):
        """Return element by key.

        For KLVParser sets, pass a bytes key. For TagParser sets, pass an int tag.
        """
        return self.items[key]

    def parse(self):
        """Parse the parent into items. Called on init and modification of parent value.

        If a known parser is not available for key, parse as generic KLV element.
        """
        if self._parser_class is TagParser:
            parser = TagParser(self.value)
        else:
            parser = KLVParser(self.value, self.key_length)

        for key, value in parser:
            try:
                self.items[key] = self.parsers[key](value)
            except (KeyError, TypeError):
                self.items[key] = self._unknown_element(key, value)
            except ValueError:
                self.items[key] = self._unknown_element(key, value)

    @classmethod
    def add_parser(cls, obj):
        """Decorator method used to register a parser to the class parsing repertoire.

        For TagParser sets, obj must implement a TAG attribute (int). For KLVParser
        sets, obj must implement a key attribute supporting bytes conversion.
        """
        if cls._parser_class is TagParser:
            key = getattr(obj, 'TAG', int.from_bytes(bytes(obj.key), 'big'))
        else:
            key = bytes(obj.key)
        cls.parsers[key] = obj

        return obj

    parsers: ClassVar[dict]

    def __repr__(self):
        return pformat(self.items, indent=1)

    def __str__(self):
        return str_dict(self.items)

    def MetadataList(self):
        ''' Return metadata dictionary'''
        metadata = {}

        def repeat(items, indent=1):
            for item in items:
                try:
                    metadata[item.TAG] = (item.LDSName, item.ESDName, item.UDSName, str(item.value.value))
                except:
                    pass
                if hasattr(item, 'items'):
                    repeat(item.items.values(), indent + 1)
        repeat(self.items.values())
        return OrderedDict(metadata)

    def structure(self):
        print(str(type(self)))

        def repeat(items, indent=1):
            for item in items:
                print(indent * "\t" + str(type(item)))
                if hasattr(item, 'items'):
                    repeat(item.items.values(), indent+1)
                else:
                    print((indent+1) * "\t" + str(item.value))

        repeat(self.items.values())


def str_dict(values):
    out = []

    def per_item(value, indent=0):
        for item in value:
            if isinstance(item, Element):
                out.append(indent * "\t" + str(item))
            else:
                out.append(indent * "\t" + str(item))

    per_item(values)

    return '\n'.join(out)
