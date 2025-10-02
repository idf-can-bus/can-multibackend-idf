#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
ESP-IDF sdkconfig file reader, parser, and writer.
Manages configuration key-value pairs with in-place updates
while preserving file structure and comments.
'''

import logging
import os
from dataclasses import dataclass
from typing import Optional, Dict, List
from py.log.rich_log_handler import LogSource, RichLogHandler

reconfig_logger = RichLogHandler.get_logger(LogSource.RECONFIG)


@dataclass
class SdkconfigLine:
    """
    Single configuration line from sdkconfig file.
    Tracks key, value, and original line text for in-place updates.
    """
    key: str
    value: str
    original_line: str

    def set_value(self, new_value: str) -> None:
        """
        Update value and regenerate line text.
        
        Args:
            new_value: New configuration value
        """
        self.value = new_value
        self.original_line = f"{self.key}={new_value}\n"

class Sdkconfig:
    """
    ESP-IDF sdkconfig file manager.
    Reads, parses, modifies, and writes sdkconfig files while preserving structure.
    Maintains line number mapping for in-place updates.
    """

    def __init__(self, sdkconfig_path: str, menu_name: str):
        """
        Initialize sdkconfig manager and load file.
        
        Args:
            sdkconfig_path: Path to sdkconfig file
            menu_name: Menu section name (for logging context)
        """
        self.sdkconfig_path = sdkconfig_path
        self.menu_name = menu_name
        self._sdkconfig_lines: Dict[str, SdkconfigLine] = {}
        self._keys_to_lines_number: Dict[str, int] = {}
        self._load_sdkconfig()

    def set_sdkconfig_path(self, sdkconfig_path: str) -> None:
        """
        Update sdkconfig file path.
        
        Args:
            sdkconfig_path: New path to sdkconfig file
        """
        self.sdkconfig_path = sdkconfig_path

    def _load_sdkconfig(self) -> None:
        """
        Load and parse sdkconfig file into memory.
        Extracts key-value pairs and tracks line numbers.
        """
        if not os.path.exists(self.sdkconfig_path):
            reconfig_logger.error(f"SDKconfig file not found at {self.sdkconfig_path}")
            return

        try:
            with open(self.sdkconfig_path, 'r') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if '=' in line:
                    key, value = line.split('=', 1)
                    self._sdkconfig_lines[key] = SdkconfigLine(key, value, line + '\n')
                    self._keys_to_lines_number[key] = i

            reconfig_logger.info(f"Loaded {len(self._sdkconfig_lines)} config options from {self.sdkconfig_path}")

        except Exception as e:
            reconfig_logger.error(f"Error loading sdkconfig: {e}")
            import traceback
            reconfig_logger.debug(traceback.format_exc())

    def _normalize_key(self, key: str) -> str:
        """
        Ensure key has CONFIG_ prefix.
        
        Args:
            key: Configuration key
            
        Returns:
            Key with CONFIG_ prefix
        """
        return key if key.startswith('CONFIG_') else f'CONFIG_{key}'

    def get_line_by_key(self, key: str) -> Optional[SdkconfigLine]:
        """
        Get configuration line by key.
        
        Args:
            key: Configuration key (with or without CONFIG_ prefix)
            
        Returns:
            SdkconfigLine or None if not found
        """
        key = self._normalize_key(key)
        return self._sdkconfig_lines.get(key)

    def add_no_existing_bool_keys(self, keys: List[str]) -> None:
        """
        Add missing boolean keys with default value 'n'.
        
        Args:
            keys: List of keys to check and add if missing
        """
        for key in keys:
            key = self._normalize_key(key)
            if key not in self._sdkconfig_lines:
                reconfig_logger.debug(f"Adding missing key: {key}")
                self._sdkconfig_lines[key] = SdkconfigLine(key, 'n', f"{key}=n\n")

    def write(self) -> None:
        """
        Write configuration to sdkconfig file with backup.
        Creates .bak backup of existing file before writing.
        """
        try:
            if os.path.exists(self.sdkconfig_path):
                backup_path = f"{self.sdkconfig_path}.bak"
                os.replace(self.sdkconfig_path, backup_path)

            with open(self.sdkconfig_path, 'w') as f:
                for line in self._sdkconfig_lines.values():
                    f.write(line.original_line)

            reconfig_logger.info(f"Successfully wrote sdkconfig to {self.sdkconfig_path}")

        except Exception as e:
            reconfig_logger.error(f"Error writing sdkconfig: {e}")
            import traceback
            reconfig_logger.debug(traceback.format_exc())
