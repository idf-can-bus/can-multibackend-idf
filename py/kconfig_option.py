#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Kconfig parser and configuration option management for ESP32 projects.
Handles parsing of Kconfig.projbuild files and extracts menu choices with dependencies.
'''

import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional
from pprint import pprint
import kconfiglib

logger = logging.getLogger(__name__)


@dataclass
class ConfigOption:
    """
    ConfigOption class
    It is used to store the configuration options from the Kconfig file
    """
    id: str  # e.g. "CAN_BACKEND_TWAI"
    display_name: str  # e.g. "Built-in TWAI (SN65HVD230)"
    config_type: str  # e.g. "bool"
    depends_on: Optional[List[str]] = None  # e.g. ["CAN_BACKEND_MCP_MULTI"]

    def __str__(self):
        return f"id: {self.id} display_name: {self.display_name} " \
               f"config_type: {self.config_type} " \
               f"depends_on: {self.depends_on}"


class KconfigMenuItems:
    """
    KconfigMenuItems class
    It is used to store the configuration options from the Kconfig file
    """

    def __init__(self, kconfig_path: str, menu_name: str):
        self._menus_dict: dict[str, dict[str, ConfigOption]] = {}
        self.kconfig_path = kconfig_path  # Fix: store the path
        self.our_menu_name = None  # Store our menu name
        self._load_kconfig_options(kconfig_path, menu_name)

    def _load_kconfig_options(self, kconfig_path: str, expectedparent_menu_name: str):
        """Load lib and example options from Kconfig file"""
        if not os.path.exists(kconfig_path):
            # print error message and exit
            logger.error(f"Kconfig file not found at {kconfig_path}")
            exit(1)

        try:
            kconf = kconfiglib.Kconfig(kconfig_path)
            logger.debug(f"Successfully loaded Kconfig from {kconfig_path}")

            # Find choices by their prompt and extract options
            for node in kconf.node_iter():
                # Check if this node is a Choice (alternative approach)
                if hasattr(node.item, 'choice') or str(type(node.item).__name__) == 'Choice':
                    # Skip choices without prompt
                    if not node.prompt:
                        continue

                    menu_name = node.prompt[0]  # e.g. "Select CAN driver/library"
                    logger.debug(f"Found choice menu: '{menu_name}'")

                    # Find the parent menu name by going up the tree
                    parent_node = node.parent
                    while parent_node:
                        if hasattr(parent_node.item, 'prompt') and parent_node.prompt:
                            parent_menu_name = parent_node.prompt[0]
                            if parent_menu_name == expectedparent_menu_name:
                                self.our_menu_name = parent_menu_name
                                logger.info(f"Found our menu section: '{parent_menu_name}'")
                                break
                        parent_node = parent_node.parent

                    # Extract all options from this choice by iterating child nodes
                    choice_child = node.list
                    while choice_child:
                        if hasattr(choice_child.item, 'name') and hasattr(choice_child.item, 'type'):
                            config_item = choice_child.item
                            logger.debug(f"  Found config: {config_item.name}")

                            # Get display name from prompt or use config name
                            display_name = choice_child.prompt[0] if choice_child.prompt else config_item.name

                            # Check for dependencies - FIXED
                            depends_on = []
                            if hasattr(config_item, 'direct_dep') and config_item.direct_dep != kconf.y:
                                dep_str = str(config_item.direct_dep)
                                logger.debug(f"    Raw dependency: {dep_str}")

                                # Extract symbol names using regex - FIXED: include digits
                                symbol_matches = re.findall(r'<symbol ([A-Z0-9_]+)', dep_str)
                                if symbol_matches:
                                    depends_on = symbol_matches
                                    logger.debug(f"    Extracted symbols: {depends_on}")

                            # Create ConfigOption
                            option = ConfigOption(
                                id=config_item.name,
                                display_name=display_name,
                                config_type=str(config_item.type),
                                depends_on=depends_on if depends_on else None
                            )

                            logger.debug(f"    Created option: {option}")

                            # Add to menus dict
                            self.add_option(menu_name, option)

                        # Move to next sibling
                        choice_child = choice_child.next

            logger.debug(f"Loaded {len(self._menus_dict)} menu(s) with total options")
            if self.our_menu_name:
                logger.info(f"Will write configs to section: {self.our_menu_name}")
            # print("self._menus_dict")
            # pprint(self._menus_dict)

        except Exception as e:
            logger.error(f"Error loading Kconfig: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            exit(1)

    def add_option(self, menu_name: str, option: ConfigOption):
        try:
            self._menus_dict[menu_name][option.id] = option
        except KeyError:
            self._menus_dict[menu_name] = {option.id: option}
        logger.debug(f"Added option {option.id} to menu '{menu_name}'")

    def get_option_by_id(self, menu_name: str, id: str, default: ConfigOption = None) -> ConfigOption:
        try:
            return self._menus_dict[menu_name][id]
        except KeyError:
            logger.warning(f"Option {id} not found in menu '{menu_name}'")
            return default

    def debug_print(self):
        logger.debug("=== KCONFIG DICTIONARY ===")
        pprint(self._menus_dict, indent=3)

    def get_all_options(self) -> dict[str, ConfigOption]:
        """Get all options from the Kconfig dictionary"""
        flat_dict = {}
        for menu_name, options in self._menus_dict.items():
            for option_id, option in options.items():
                flat_dict[option_id] = option
        return flat_dict 