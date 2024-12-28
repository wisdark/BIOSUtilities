#!/usr/bin/env python3 -B
# coding=utf-8

"""
VAIO Package Extractor
VAIO Packaging Manager Extractor
Copyright (C) 2019-2024 Plato Mavropoulos
"""

import os

from re import Match

from biosutilities.common.compression import is_szip_supported, szip_decompress
from biosutilities.common.paths import delete_file, make_dirs, path_name
from biosutilities.common.patterns import PAT_VAIO_CAB, PAT_VAIO_CFG, PAT_VAIO_CHK, PAT_VAIO_EXT
from biosutilities.common.system import printer
from biosutilities.common.templates import BIOSUtility


class VaioPackageExtract(BIOSUtility):
    """ VAIO Packaging Manager Extractor """

    TITLE: str = 'VAIO Packaging Manager Extractor'

    def check_format(self) -> bool:
        """ Check if input is VAIO Packaging Manager """

        return bool(PAT_VAIO_CFG.search(self.input_buffer))

    def parse_format(self) -> bool:
        """ Parse & Extract or Unlock VAIO Packaging Manager """

        input_name: str = path_name(self.input_object) if isinstance(self.input_object, str) else 'VAIO_Package'

        make_dirs(in_path=self.extract_path)

        if self._vaio_cabinet(name=input_name, buffer=self.input_buffer, extract_path=self.extract_path,
                              padding=self.padding) == 0:
            printer(message='Successfully Extracted!', padding=self.padding)
        elif self._vaio_unlock(name=input_name, buffer=self.input_buffer, extract_path=self.extract_path,
                               padding=self.padding) == 0:
            printer(message='Successfully Unlocked!', padding=self.padding)
        else:
            printer(message='Error: Failed to Extract or Unlock executable!', padding=self.padding)

            return False

        return True

    @staticmethod
    def _vaio_cabinet(name: str, buffer: bytes | bytearray, extract_path: str, padding: int = 0) -> int:
        """ Extract VAIO Packaging Manager executable """

        # Microsoft CAB Header XOR 0xFF
        match_cab: Match[bytes] | None = PAT_VAIO_CAB.search(buffer)

        if not match_cab:
            return 1

        printer(message='Detected obfuscated CAB archive!', padding=padding)

        # Get LE XOR CAB size
        cab_size: int = int.from_bytes(buffer[match_cab.start() + 0x8:match_cab.start() + 0xC], byteorder='little')

        # Create CAB size XOR value
        xor_size: int = int.from_bytes(b'\xFF' * 0x4, byteorder='little')

        # Perform XOR 0xFF and get actual CAB size
        cab_size ^= xor_size

        printer(message='Removing obfuscation...', padding=padding + 4)

        # Get BE XOR CAB data
        cab_data: int = int.from_bytes(buffer[match_cab.start():match_cab.start() + cab_size], byteorder='big')

        # Create CAB data XOR value
        xor_data: int = int.from_bytes(b'\xFF' * cab_size, byteorder='big')

        # Perform XOR 0xFF and get actual CAB data
        raw_data: bytes = (cab_data ^ xor_data).to_bytes(cab_size, 'big')

        printer(message='Extracting archive...', padding=padding + 4)

        cab_path: str = os.path.join(extract_path, f'{name}_Temporary.cab')

        # Create temporary CAB archive
        with open(cab_path, 'wb') as cab_file:
            cab_file.write(raw_data)

        if is_szip_supported(in_path=cab_path):
            if szip_decompress(in_path=cab_path, out_path=extract_path, in_name='VAIO CAB',
                               padding=padding + 8, check=True):
                delete_file(in_path=cab_path)
            else:
                return 3
        else:
            return 2

        return 0

    @staticmethod
    def _vaio_unlock(name: str, buffer: bytes | bytearray, extract_path: str, padding: int = 0) -> int:
        """ Unlock VAIO Packaging Manager executable """

        input_buffer: bytearray = bytearray(buffer) if isinstance(buffer, bytes) else buffer

        match_cfg: Match[bytes] | None = PAT_VAIO_CFG.search(input_buffer)

        if not match_cfg:
            return 1

        printer(message='Attempting to Unlock executable!', padding=padding)

        # Initialize VAIO Package Configuration file variables (assume overkill size of 0x500)
        cfg_bgn, cfg_end, cfg_false, cfg_true = [match_cfg.start(), match_cfg.start() + 0x500, b'', b'']

        # Get VAIO Package Configuration file info, split at new_line and stop at payload DOS header (EOF)
        cfg_info: list[bytearray] = input_buffer[cfg_bgn:cfg_end].split(
            b'\x0D\x0A\x4D\x5A')[0].replace(b'\x0D', b'').split(b'\x0A')

        printer(message='Retrieving True/False values...', padding=padding + 4)

        # Determine VAIO Package Configuration file True & False values
        for info in cfg_info:
            if info.startswith(b'ExtractPathByUser='):
                # Should be 0/No/False
                cfg_false = bytearray(b'0' if info[18:] in (b'0', b'1') else info[18:])

            if info.startswith(b'UseCompression='):
                # Should be 1/Yes/True
                cfg_true = bytearray(b'1' if info[15:] in (b'0', b'1') else info[15:])

        # Check if valid True/False values have been retrieved
        if cfg_false == cfg_true or not cfg_false or not cfg_true:
            printer(message='Error: Could not retrieve True/False values!', padding=padding + 8)

            return 2

        printer(message='Adjusting UseVAIOCheck entry...', padding=padding + 4)

        # Find and replace UseVAIOCheck entry from 1/Yes/True to 0/No/False
        vaio_check: Match[bytes] | None = PAT_VAIO_CHK.search(input_buffer[cfg_bgn:])

        if vaio_check:
            input_buffer[cfg_bgn + vaio_check.end():cfg_bgn + vaio_check.end() + len(cfg_true)] = cfg_false
        else:
            printer(message='Error: Could not find entry UseVAIOCheck!', padding=padding + 8)

            return 3

        printer(message='Adjusting ExtractPathByUser entry...', padding=padding + 4)

        # Find and replace ExtractPathByUser entry from 0/No/False to 1/Yes/True
        user_path: Match[bytes] | None = PAT_VAIO_EXT.search(input_buffer[cfg_bgn:])

        if user_path:
            input_buffer[cfg_bgn + user_path.end():cfg_bgn + user_path.end() + len(cfg_false)] = cfg_true
        else:
            printer(message='Error: Could not find entry ExtractPathByUser!', padding=padding + 8)

            return 4

        printer(message='Storing unlocked executable...', padding=padding + 4)

        # Store Unlocked VAIO Packaging Manager executable
        if vaio_check and user_path:
            unlock_path: str = os.path.join(extract_path, f'{name}_Unlocked.exe')

            with open(unlock_path, 'wb') as unl_file:
                unl_file.write(input_buffer)

        return 0
