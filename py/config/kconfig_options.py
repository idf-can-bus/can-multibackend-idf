#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Kconfig.projbuild parser for ESP-IDF project configuration.
Extracts menu choices, config options, and dependency relationships
using kconfiglib for structured configuration management.
'''

import logging
import os
import re
from dataclasses import dataclass
from typing import List, Optional
from pprint import pprint
import kconfiglib
from py.log.rich_log_handler import LogSource, RichLogHandler

logger = RichLogHandler.get_logger(LogSource.CONFIG)


@dataclass
class ConfigOption:
    """
    Configuration option from Kconfig file.
    Represents a single choice option with ID, display name, type, and dependencies.
    """
    id: str
    display_name: str
    config_type: str
    depends_on: Optional[List[str]] = None

    def __str__(self):
        return (
            f"id: {self.id} display_name: {self.display_name} "
            f"config_type: {self.config_type} "
            f"depends_on: {self.depends_on}"
        )


class KconfigMenuItems:
    """
    Kconfig menu parser and option manager.
    Loads Kconfig.projbuild file and extracts choice menus with their options and dependencies.
    Organizes options by menu name for easy access.
    """

    def __init__(self, kconfig_path: str, menu_name: str):
        """
        Initialize and load Kconfig options.
        
        Args:
            kconfig_path: Path to Kconfig.projbuild file
            menu_name: Parent menu name to search for
        """
        self._menus_dict: dict[str, dict[str, ConfigOption]] = {}
        self.kconfig_path = kconfig_path
        self.our_menu_name = None
        self._load_kconfig_options(kconfig_path, menu_name)

    def _load_kconfig_options(self, kconfig_path: str, expectedparent_menu_name: str):
        """
        Parse Kconfig file and extract choice menus with options.
        
        Args:
            kconfig_path: Path to Kconfig file
            expectedparent_menu_name: Parent menu name to match
        """
        if not os.path.exists(kconfig_path):
            logger.error(f"Kconfig file not found at {kconfig_path}")
            exit(1)

        try:
            kconf = kconfiglib.Kconfig(kconfig_path)
            logger.debug(f"Successfully loaded Kconfig from {kconfig_path}")

            for node in kconf.node_iter():
                if hasattr(node.item, 'choice') or str(type(node.item).__name__) == 'Choice':
                    if not node.prompt:
                        continue

                    menu_name = node.prompt[0]
                    logger.debug(f"Found choice menu: '{menu_name}'")

                    parent_node = node.parent
                    while parent_node:
                        if hasattr(parent_node.item, 'prompt') and parent_node.prompt:
                            parent_menu_name = parent_node.prompt[0]
                            if parent_menu_name == expectedparent_menu_name:
                                self.our_menu_name = parent_menu_name
                                logger.info(f"Found our menu section: '{parent_menu_name}'")
                                break
                        parent_node = parent_node.parent

                    choice_child = node.list
                    while choice_child:
                        if hasattr(choice_child.item, 'name') and hasattr(choice_child.item, 'type'):
                            config_item = choice_child.item
                            logger.debug(f"  Found config: {config_item.name}")

                            display_name = choice_child.prompt[0] if choice_child.prompt else config_item.name

                            depends_on = []
                            if hasattr(config_item, 'direct_dep') and config_item.direct_dep != kconf.y:
                                dep_str = str(config_item.direct_dep)
                                logger.debug(f"    Raw dependency: {dep_str}")

                                symbol_matches = re.findall(r'<symbol ([A-Z0-9_]+)', dep_str)
                                if symbol_matches:
                                    depends_on = symbol_matches
                                    logger.debug(f"    Extracted symbols: {depends_on}")

                            option = ConfigOption(
                                id=config_item.name,
                                display_name=display_name,
                                config_type=str(config_item.type),
                                depends_on=depends_on if depends_on else None
                            )

                            logger.debug(f"    Created option: {option}")
                            self.add_option(menu_name, option)

                        choice_child = choice_child.next

            logger.debug(f"Loaded {len(self._menus_dict)} menu(s) with total options")
            if self.our_menu_name:
                logger.info(f"Will write configs to section: {self.our_menu_name}")

        except Exception as e:
            logger.error(f"Error loading Kconfig: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            exit(1)

    def add_option(self, menu_name: str, option: ConfigOption):
        """
        Add configuration option to menu.
        
        Args:
            menu_name: Menu to add option to
            option: ConfigOption to add
        """
        try:
            self._menus_dict[menu_name][option.id] = option
        except KeyError:
            self._menus_dict[menu_name] = {option.id: option}
        logger.debug(f"Added option {option.id} to menu '{menu_name}'")

    def get_option_by_id(self, menu_name: str, id: str, default: ConfigOption = None) -> ConfigOption:
        """
        Get configuration option by ID.
        
        Args:
            menu_name: Menu name to search in
            id: Option ID
            default: Default value if not found
            
        Returns:
            ConfigOption or default
        """
        try:
            return self._menus_dict[menu_name][id]
        except KeyError:
            logger.warning(f"Option {id} not found in menu '{menu_name}'")
            return default

    def debug_print(self):
        """Print all menus and options for debugging."""
        logger.debug("=== KCONFIG DICTIONARY ===")
        pprint(self._menus_dict, indent=3)

    def get_all_options(self) -> dict[str, ConfigOption]:
        """
        Get all options from all menus as flat dictionary.
        
        Returns:
            Dictionary mapping option IDs to ConfigOption instances
        """
        flat_dict = {}
        for menu_name, options in self._menus_dict.items():
            for option_id, option in options.items():
                flat_dict[option_id] = option
        return flat_dict
