#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
SDKconfig file management for ESP32 projects.
Handles reading, parsing, and updating of ESP-IDF sdkconfig files.
'''

import logging
import os
from dataclasses import dataclass
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

@dataclass
class SdkconfigLine:
    """
    Represents a single line in sdkconfig file.
    Contains the key, value and original line content.
    """
    key: str
    value: str
    original_line: str

    def set_value(self, new_value: str) -> None:
        """Update the value and original line"""
        self.value = new_value
        self.original_line = f"{self.key}={new_value}\n"

class Sdkconfig:
    """
    Class for managing ESP-IDF sdkconfig files.
    Handles reading, parsing and updating of configuration values.
    """

    def __init__(self, sdkconfig_path: str, menu_name: str):
        """
        Initialize Sdkconfig with path to sdkconfig file.
        
        Args:
            sdkconfig_path: Path to sdkconfig file
            menu_name: Name of the menu section to manage
        """
        self.sdkconfig_path = sdkconfig_path
        self.menu_name = menu_name
        self._sdkconfig_lines: Dict[str, SdkconfigLine] = {}
        self._keys_to_lines_number: Dict[str, int] = {}
        
        # Load existing sdkconfig
        self._load_sdkconfig()

    def _load_sdkconfig(self) -> None:
        """Load and parse sdkconfig file"""
        if not os.path.exists(self.sdkconfig_path):
            logger.error(f"SDKconfig file not found at {self.sdkconfig_path}")
            return

        try:
            with open(self.sdkconfig_path, 'r') as f:
                lines = f.readlines()

            # Parse each line
            for i, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    self._sdkconfig_lines[key] = SdkconfigLine(key, value, line + '\n')
                    self._keys_to_lines_number[key] = i

            logger.info(f"Loaded {len(self._sdkconfig_lines)} config options from {self.sdkconfig_path}")

        except Exception as e:
            logger.error(f"Error loading sdkconfig: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    def _normalize_key(self, key: str) -> str:
        return key if key.startswith('CONFIG_') else f'CONFIG_{key}'

    def get_line_by_key(self, key: str) -> Optional[SdkconfigLine]:
        """Get SdkconfigLine for given key"""
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
                logger.debug(f"Adding missing key: {key}")
                self._sdkconfig_lines[key] = SdkconfigLine(key, 'n', f"{key}=n\n")

    def write(self) -> None:
        """Write current configuration to sdkconfig file"""
        try:
            # Create backup of current sdkconfig
            if os.path.exists(self.sdkconfig_path):
                backup_path = f"{self.sdkconfig_path}.bak"
                os.replace(self.sdkconfig_path, backup_path)

            # Write new sdkconfig
            with open(self.sdkconfig_path, 'w') as f:
                for line in self._sdkconfig_lines.values():
                    f.write(line.original_line)

            logger.info(f"Successfully wrote sdkconfig to {self.sdkconfig_path}")

        except Exception as e:
            logger.error(f"Error writing sdkconfig: {e}")
            import traceback
            logger.debug(traceback.format_exc()) 