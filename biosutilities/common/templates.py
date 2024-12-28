#!/usr/bin/env python3 -B
# coding=utf-8

"""
Copyright (C) 2022-2024 Plato Mavropoulos
"""

from biosutilities.common.paths import runtime_root
from biosutilities.common.texts import file_to_bytes


class BIOSUtility:
    """ Base class for BIOSUtilities """

    TITLE: str = 'BIOS Utility'

    def __init__(self, input_object: str | bytes | bytearray = b'', extract_path: str = runtime_root(),
                 padding: int = 0) -> None:
        self.input_object: str | bytes | bytearray = input_object
        self.extract_path: str = extract_path
        self.padding: int = padding

        self.__input_buffer: bytes = b''

    @property
    def input_buffer(self) -> bytes:
        """ Get input object buffer """

        if not self.__input_buffer:
            self.__input_buffer = file_to_bytes(in_object=self.input_object)

        return self.__input_buffer

    def check_format(self) -> bool:
        """ Check if input object is of specific supported format """

        raise NotImplementedError(f'Method "check_format" not implemented at {__name__}')

    def parse_format(self) -> bool:
        """ Process input object as a specific supported format """

        raise NotImplementedError(f'Method "parse_format" not implemented at {__name__}')
