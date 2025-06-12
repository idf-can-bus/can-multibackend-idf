#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
ESP32 Flash Tool
'''

import subprocess
import glob
import argparse
import os
import logging
import kconfiglib
import re
import shutil
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Checkbox, Select, RichLog, Footer
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive
from pprint import pprint

# Custom logging handler for RichLog
class RichLogHandler(logging.Handler):
    """
    Custom logging handler for RichLog
    This class is used to log messages to a RichLog widget
    It is used to display the log messages in a more readable format.
    """
    def __init__(self):
        super().__init__()
        self.rich_log = None
    
    def set_rich_log(self, rich_log: RichLog):
        self.rich_log = rich_log
    
    def emit(self, record):
        if self.rich_log:
            msg = self.format(record)
            self.rich_log.write(msg)

# Configure logging with custom handler
rich_log_handler = RichLogHandler()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s',
    handlers=[rich_log_handler]
)
logger = logging.getLogger(__name__)

@dataclass
class ConfigOption:
    """
    ConfigOption class
    It is used to store the configuration options from the Kconfig file
    """
    id: str             # e.g. "CAN_BACKEND_TWAI"
    display_name: str   # e.g. "Built-in TWAI (SN65HVD230)"
    config_type: str    # e.g. "bool"
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
                            if parent_menu_name==expectedparent_menu_name:
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

# --- end of KconfigMenuItems class ---
# enumerate type for type of sdkconfig line as COMMENT, BOOL, INT, START_SECTION, END_SECTION, OTHER
class SdkconfigLineType(Enum):
    BOOL = auto()
    INT = auto()
    OTHER_KEY_VALUE = auto()  # placeholder for not implemented other key=value lines
    NOT_KEY_VALUE = auto()    # comments and other lines that are not key=value lines
    START_SECTION = auto()    # tag for line wich is recognited as start of section 
    END_SECTION = auto()      # tag for line wich is recognited as end of section 
   
@dataclass
class SdkconfigLine:
    """
    SdkconfigLine class
    It is used to store the sdkconfig lines
    """
    raw_str: str
    number: int
    type: str
    var_name: str
    value: str
    is_changed: bool
    is_commented: bool

    def __init__(self, raw_str: str, number: int=None):
        self._set_from_raw_str(raw_str, number)

    def _set_from_raw_str(self, raw_str: str, number: int):
        """Set the sdkconfig line from a raw string"""
        self.raw_str = raw_str
        self.number = number
        self.is_changed = False  # is_changed flag is set later if value is changed
        tmp_str = raw_str.strip()
        
        if tmp_str.startswith('#'):
            self.is_commented = True
            tmp_str = tmp_str[1:].strip()
        else:
            self.is_commented = False
        
        # Check for "CONFIG_XXX is not set" format (can be commented or not)
        if tmp_str.startswith('CONFIG_') and tmp_str.endswith(' is not set'):
            # Handle "CONFIG_XXX is not set" format
            parts = tmp_str.split(' is not set')
            self.var_name = parts[0][len('CONFIG_'):].strip()
            self.value = 'n'
            self.type = SdkconfigLineType.BOOL
            self.is_commented = False
        # Parse other CONFIG_ lines
        elif tmp_str.startswith('CONFIG_'):     
            if '=' in tmp_str:
                parts = tmp_str.split('=', 1)
                self.var_name = parts[0].strip()[len('CONFIG_'):]
                self.value = parts[1].strip()
                # Recognize type of value
                if self.value in ['y', 'n']:
                    self.type = SdkconfigLineType.BOOL
                elif self.value.isdigit():
                    self.type = SdkconfigLineType.INT
                else:
                    self.type = SdkconfigLineType.OTHER_KEY_VALUE
            else:
                self.var_name = None
                self.value = None
                self.type = SdkconfigLineType.NOT_KEY_VALUE
        else:
            self.var_name = None
            self.value = None
            self.type = SdkconfigLineType.NOT_KEY_VALUE

    def set_value(self, new_value: str):
        self.value = new_value
        self.is_changed = True

    def _write_to_file(self, opened_file):
        if not self.is_changed:
            opened_file.write(self.raw_str)
        else:
            if self.type == SdkconfigLineType.BOOL:
                if self.value == 'y':
                    opened_file.write(f"CONFIG_{self.var_name} = y\n")
                else:
                    opened_file.write(f"# CONFIG_{self.var_name} is not set\n")
            elif self.type == SdkconfigLineType.INT:
                opened_file.write(f"CONFIG_{self.var_name} = {self.value}\n")
            elif self.type == SdkconfigLineType.OTHER_KEY_VALUE:
                opened_file.write(f"CONFIG_{self.var_name} = {self.value}\n")
            else:
                opened_file.write(f"{self.raw_str}\n")


class Sdkconfig:
    """
    Sdkconfig class
    It is used to store the sdkconfig lines and manage them.
    """

    def __init__(self, sdkconfig_path: str, section_name: str):
        self._sdkconfig_lines, self._keys_to_lines_number = self._load_sdkconfig(sdkconfig_path)
        self._sdkconfig_path = sdkconfig_path
        self._section_name = section_name
        
        
    def _load_sdkconfig(self, sdkconfig_path: str) -> tuple[list[SdkconfigLine], dict[str, int]]:
        """Load sdkconfig file"""
        lines = []
        keys_to_lines_number = {}
        if not os.path.exists(sdkconfig_path):
            logger.error(f"Sdkconfig file not found at {sdkconfig_path}")
            exit(1)
        
        with open(sdkconfig_path, 'r', encoding='utf-8') as f:
            for line_number, line_str in enumerate(f):
                line_obj = SdkconfigLine(line_str, line_number)
                lines.append(line_obj)
                if line_obj.var_name is not None:
                    keys_to_lines_number[line_obj.var_name] = line_number
        return lines, keys_to_lines_number

    def _backup_to_rotated_file(self, max_backups: int = 5) -> bool:
        """
        Backup original sdkfile to .backup.1, .backup.2, etc.
        """
        if not os.path.exists(self._sdkconfig_path):
            logger.error(f"Sdkconfig file not found at {self._sdkconfig_path}")
            return False
        
        # rotate backups
        sdkconfig_path = self._sdkconfig_path
        try:
            # Rotate existing backups
            for i in range(max_backups - 1, 0, -1):
                old_backup = f"{sdkconfig_path}.backup.{i}"
                new_backup = f"{sdkconfig_path}.backup.{i + 1}"
                
                if os.path.exists(old_backup):
                    if i == max_backups - 1:
                        # Delete the oldest backup
                        os.remove(old_backup)
                        logger.debug(f"Deleted oldest backup: {old_backup}")
                    else:
                        # Move to next backup slot
                        os.rename(old_backup, new_backup)
                        logger.debug(f"Rotated backup: {old_backup} -> {new_backup}")
            
            # Create new backup from current file
            if os.path.exists(sdkconfig_path):
                backup_path = f"{sdkconfig_path}.backup.1"
                shutil.copy2(sdkconfig_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate backups: {e}")
            return False
        
    def write(self):
        """Write sdkconfig file"""
        if not self._backup_to_rotated_file():
            logger.error("Failed to create backup - aborting sdkconfig update")
            return
        
        with open(self._sdkconfig_path, 'w', encoding='utf-8') as f:
            for line in self._sdkconfig_lines:
                line._write_to_file(f)

    def get_lines(self) -> list[SdkconfigLine]:
        """Get sdkconfig lines"""
        return self._sdkconfig_lines
    
    def get_line_by_number(self, number: int) -> SdkconfigLine:
        """Get sdkconfig line by number"""
        try:
            return self._sdkconfig_lines[number]
        except IndexError:
            logger.error(f"get_line_by_number: Line number {number} not found in sdkconfig")
            return None
    
    def get_line_by_key(self, key: str) -> SdkconfigLine:
        """Get sdkconfig line by key"""
        try:
            return self._sdkconfig_lines[self._keys_to_lines_number[key]]
        except KeyError:
            logger.error(f"get_line_by_key: Key {key} not found in sdkconfig")
            return None
        
    def get_lines_and_missing_keys(self, expected_keys: list[str]) -> (dict[int, SdkconfigLine], list[str]):
        """
        Get sdkconfig lines by keys and missing keys
        Returns:
            lines: dict[int, SdkconfigLine] - sdkconfig lines
            missing_keys: list[str] - missing keys
        """
        lines = {}
        missing_keys = []
        for expected_key in expected_keys: 
            sdkconfig_line = self.get_line_by_key(expected_key)
            if sdkconfig_line:
                lines[sdkconfig_line.number] = sdkconfig_line
            else:
                missing_keys.append(expected_key)
        return lines, missing_keys
    
    def add_no_existing_bool_keys(self, expected_keys: list[str]) -> bool:
        """Add missing CONFIG keys to sdkconfig at appropriate position"""
        lines_dict, missing_keys = self.get_lines_and_missing_keys(expected_keys)

        if not missing_keys:
            return True
        
        new_lines = []
        insert_position = None
        
        new_section_added = False
        if lines_dict:
            insert_position = max(lines_dict.keys()) + 1
        else:
            # find "# Deprecated options for backward compatibility" line
            for i, line in enumerate(self._sdkconfig_lines):
                if line.raw_str.startswith("# Deprecated options for backward compatibility"):
                    insert_position = i - 1
                    # add new section lines 
                    #
                    # *** Example to build ***
                    #
                    new_lines = [
                        SdkconfigLine(f"#\n"),
                        SdkconfigLine(f"# {self._section_name}\n"),
                        SdkconfigLine(f"#\n"),
                    ]
                    new_section_added = True
                    break
                
            if insert_position is None:
                # add to the end of the file
                insert_position = len(self._sdkconfig_lines)

            
        logger.info(f"Adding {len(missing_keys)} missing CONFIG keys at position {insert_position}")
        
        # Add new SdkconfigLine objects for missing keys
        for key in missing_keys:
            # Create commented "is not set" line for missing keys (default to 'n')
            raw_line = f"# CONFIG_{key} is not set\n"
            new_line = SdkconfigLine(raw_line, insert_position + len(new_lines))
            new_lines.append(new_line)
            logger.debug(f"Created new line for {key}: {raw_line.strip()}")
            
        if new_section_added:
            # add "end of section" line
            new_lines.append(SdkconfigLine(f"# end of {self._section_name}\n", insert_position))
            
        # Insert new lines at the calculated position
        for i, new_line in enumerate(new_lines):
            new_line.number = insert_position + i
            self._sdkconfig_lines.insert(new_line.number, new_line)
        
        # Renumber all lines after insertion point
        self._renumber_lines_after(insert_position)
        
        # Update the keys_to_lines_number index
        self._rebuild_keys_index()
        
        logger.info(f"Successfully added {len(missing_keys)} missing CONFIG keys")
        return True
            
    
    def _renumber_lines_after(self, start_position: int = 0):
        """Renumber all lines after the given position"""
        for i in range(start_position, len(self._sdkconfig_lines)):
            self._sdkconfig_lines[i].number = i
    
    def _rebuild_keys_index(self):
        """Rebuild the keys_to_lines_number index"""
        self._keys_to_lines_number = {}
        for i, line in enumerate(self._sdkconfig_lines):
            if line.var_name is not None:
                self._keys_to_lines_number[line.var_name] = i


class FlashAppLogic:
    """
    Logic class for ESP32 flash operations
    Handles all business logic separate from GUI
    """
    
    def __init__(
        self, 
        kconfig_path: str = "./main/Kconfig.projbuild", 
        sdkconfig_path: str = "./sdkconfig", 
        gui_app=None,
        menu_name: str = "*** Example to build ***"
    ):
        self.kconfig_path = kconfig_path
        self.sdkconfig_path = sdkconfig_path
        self.gui_app = gui_app  # Optional reference to GUI
        
        # Load KconfigMenuItems for direct access
        self.kconfig_dict = KconfigMenuItems(kconfig_path, menu_name)
        
        # Load sdkconfig
        self.sdkconfig = Sdkconfig(sdkconfig_path, menu_name)

        # Check for missing CONFIG keys and add them to sdkconfig
        self.sdkconfig.add_no_existing_bool_keys(self.kconfig_dict.get_all_options().keys())
                
        # # Debug: Print loaded sdkconfig lines
        # print("=== _sdkconfig_lines ===")
        # pprint(self.sdkconfig._sdkconfig_lines)
        # print("=== _keys_to_lines_number ===")
        # pprint(self.sdkconfig._keys_to_lines_number)
        # exit(1)
        
        # Load configuration options (for backward compatibility)
        self.lib_options, self.example_options = self.load_kconfig_options(kconfig_path)

    def get_lib_option_by_id(self, lib_id: str) -> Optional[ConfigOption]:
        """Find lib option by ID using KconfigMenuItems"""
        return self.kconfig_dict.get_option_by_id("Select CAN driver/library", lib_id)

    def get_example_option_by_id(self, example_id: str) -> Optional[ConfigOption]:
        """Find example option by ID using KconfigMenuItems"""
        return self.kconfig_dict.get_option_by_id("Select example", example_id)

    def check_dependencies(self, lib_id: str, example_id: str) -> bool:
        """Check if selected lib satisfies ALL example dependencies"""
        if not lib_id or not example_id:
            return False
            
        lib_option = self.get_lib_option_by_id(lib_id)
        example_option = self.get_example_option_by_id(example_id)
        
        logger.debug(f"lib_id='{lib_id}', lib_option={lib_option}")
        logger.debug(f"example_id='{example_id}', example_option={example_option}")
        
        if not lib_option or not example_option:
            logger.debug("One or both options not found")
            return False
            
        # If example has no dependencies, it's always compatible
        if not example_option.depends_on:
            logger.debug("No dependencies required - compatible")
            return True
            
        # Check if selected lib ID is in the depends_on list
        if lib_option.id in example_option.depends_on:
            logger.debug(f"{lib_option.id} found in dependencies {example_option.depends_on} -> OK")
            return True
        else:
            logger.debug(f"{lib_option.id} NOT found in dependencies {example_option.depends_on} -> FAIL")
            return False

    def update_sdkconfig(self, lib_id: str, example_id: str) -> bool:
        """Update sdkconfig using new Sdkconfig classes"""
        try:
            logger.info(f"Updating sdkconfig for lib='{lib_id}' and example='{example_id}'")
            
            # Step 1: Get all config option IDs from KconfigMenuItems
            all_options = self.kconfig_dict.get_all_options()
            config_ids = list(all_options.keys())
            logger.debug(f"Found {len(config_ids)} config options: {config_ids}")
            
            # Step 2: Find relevant SdkconfigLines for these IDs
            relevant_lines = {}
            for config_id in config_ids:
                line = self.sdkconfig.get_line_by_key(config_id)
                if line:
                    relevant_lines[config_id] = line
                    logger.debug(f"Found existing line for {config_id}: {line.value}")
                else:
                    logger.debug(f"Config {config_id} not found in sdkconfig (should have been added during initialization)")
            
            # Step 3: Set values based on selections
            changes_made = 0
            for config_id, line in relevant_lines.items():
                new_value = None
                
                # Determine new value based on selection
                if config_id == lib_id:
                    new_value = 'y'
                    logger.info(f"ENABLE: {config_id} (selected lib)")
                elif config_id == example_id:
                    new_value = 'y' 
                    logger.info(f"ENABLE: {config_id} (selected example)")
                else:
                    new_value = 'n'
                    logger.debug(f"DISABLE: {config_id} (not selected)")
                
                # Update line if value changed
                if line.value != new_value:
                    line.set_value(new_value)
                    changes_made += 1
                    logger.debug(f"Changed {config_id}: {line.value} -> {new_value}")
            
            # Step 4: Write sdkconfig if any changes were made
            if changes_made > 0:
                logger.info(f"Writing sdkconfig with {changes_made} changes")
                self.sdkconfig.write()
                logger.info("Successfully updated sdkconfig")
            else:
                logger.info("No changes needed in sdkconfig")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update sdkconfig: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def compile_code(self, port: str, lib_id: str, example_id: str) -> bool:
        """Compile the C/C++ code for selected configuration"""
        try:
            logger.info(f"Compiling code for {lib_id}/{example_id}")
            # TODO: Implement actual compilation
            # - Run idf.py build or similar command
            # - Monitor compilation output
            # - Check for compilation errors
            
            # Placeholder implementation
            logger.info("Compilation successful")
            return True
            
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            return False

    def upload_to_port(self, port: str, lib_id: str, example_id: str) -> bool:
        """Upload compiled firmware to ESP32 on specified port"""
        try:
            logger.info(f"Uploading firmware to ESP32 on port {port}")
            # TODO: Implement actual upload
            # - Run idf.py flash -p /dev/{port} or similar command
            # - Monitor upload progress
            # - Check for upload errors
            
            # Placeholder implementation
            logger.info(f"Successfully uploaded firmware to {port}")
            return True
            
        except Exception as e:
            logger.error(f"Upload to {port} failed: {e}")
            return False

    def config_compile_flash(self, port: str, lib_id: str, example_id: str) -> bool:
        """
        Execute complete flash sequence: update config, compile, upload
        Returns True if all steps successful, False if any step fails
        """
        # Step 1: Update sdkconfig using app method
        if not self.update_sdkconfig(lib_id, example_id):
            logger.error("Flash sequence aborted: sdkconfig update failed")
            return False
        
        # Step 2: Compile code
        if not self.compile_code(port, lib_id, example_id):
            logger.error("Flash sequence aborted: compilation failed")
            return False
        
        # Step 3: Upload to ESP32
        if not self.upload_to_port(port, lib_id, example_id):
            logger.error("Flash sequence aborted: upload failed")
            return False
        
        return True

    def find_flash_ports(self, default_ports: list[str]=['Port1', 'Port2', 'Port3', 'Port4']):
        """Find available flash ports"""
        ports = glob.glob('/dev/ttyACM*')
        flash_ports1 = sorted(p[5:] for p in ports if re.match(r'/dev/ttyACM\d+$', p))
        ports = glob.glob('/dev/ttyUSB*')
        flash_ports2 = sorted(p[5:] for p in ports if re.match(r'/dev/ttyUSB\d+$', p))
        flash_ports = flash_ports1 + flash_ports2
        if flash_ports == []:
            return default_ports
        else:
            return flash_ports

    def load_kconfig_options(self, kconfig_path: str) -> tuple[List[ConfigOption], List[ConfigOption]]:
        """Load lib and example options from Kconfig file using KconfigMenuItems"""
        
        # Extract lib options from "Select CAN driver/library" menu
        lib_menu = "Select CAN driver/library"
        lib_options = []
        if lib_menu in self.kconfig_dict._menus_dict:
            for option in self.kconfig_dict._menus_dict[lib_menu].values():
                # Convert new ConfigOption to old format for compatibility
                lib_options.append(ConfigOption(
                    id=option.id,
                    display_name=option.display_name,
                    config_type=option.config_type,
                    depends_on=option.depends_on
                ))
        
        # Extract example options from "Select example" menu  
        example_menu = "Select example"
        example_options = []
        if example_menu in self.kconfig_dict._menus_dict:
            for option in self.kconfig_dict._menus_dict[example_menu].values():
                # Convert new ConfigOption to old format for compatibility
                example_options.append(ConfigOption(
                    id=option.id,
                    display_name=option.display_name,
                    config_type=option.config_type,
                    depends_on=option.depends_on
                ))
        
        return lib_options, example_options


class FlashAppGui(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #reload {
        background: orange;
        color: black;
    }
    
    #table {
        grid-size: 4;
        grid-gutter: 0 1;
        grid-rows: auto;
        height: auto;
    }
    
    .header {
        text-style: bold;
        background: $surface;
        height: 3;
        content-align: center middle;
    }
    
    #table > * {
        content-align: center middle;
    }
    
    #table Button {
        width: 95%;
        content-align: center middle;
        text-align: center;
    }
    
    #status {
        width: 100%;
        height: 1fr;
        margin: 1 0;
        border: solid $primary;
    }
    
    """
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    ports = reactive(list)

    def __init__(self, kconfig_path: str = "./main/Kconfig.projbuild", sdkconfig_path: str = "./sdkconfig"):
        super().__init__()
        
        # Create logic instance with reference to this GUI
        self.logic = FlashAppLogic(kconfig_path, sdkconfig_path, gui_app=self, menu_name="*** Example to build ***")
        
        # Initialize ports
        self.ports = self.logic.find_flash_ports()


    def compose(self) -> ComposeResult:
        yield Button("Reload ports", id="reload")

        with Grid(id="table"):
            # Headers
            yield Static("Port", classes="header")
            yield Static("Lib", classes="header")
            yield Static("Example", classes="header")
            yield Static("Flash", classes="header")

            # Rows for each port
            for port in self.ports:
                yield Static(port, classes="port")
                
                # Create lib select - use (display_name, id) format
                lib_choices = [(opt.display_name, opt.id) for opt in self.logic.lib_options]
                lib_select = Select(lib_choices, prompt="-- Select Lib --")
                
                # Create example select - use (display_name, id) format  
                example_choices = [(opt.display_name, opt.id) for opt in self.logic.example_options]
                example_select = Select(example_choices, prompt="-- Select Example --")
                
                flash_button = Button(f"Flash {port}", id=f"flash-{port}", disabled=True)
                                
                yield lib_select
                yield example_select
                yield flash_button

        yield RichLog(highlight=True, id="status", name="testarea")
        yield Footer()

    def on_mount(self) -> None:
        # Connect the logging handler to RichLog
        rich_log_handler.set_rich_log(self.query_one(RichLog))
        
        # Log config file paths and loaded options on startup
        logger.info(f"Kconfig: {self.logic.kconfig_path}")
        logger.info(f"SDKconfig: {self.logic.sdkconfig_path}")
        logger.info(f"Loaded {len(self.logic.lib_options)} lib options, {len(self.logic.example_options)} example options")
        
        # Debug: Print all loaded options
        logger.debug("=== LIB OPTIONS ===")
        for opt in self.logic.lib_options:
            logger.debug(f"  {opt.id}: {opt.display_name}")
        
        logger.debug("=== EXAMPLE OPTIONS ===")
        for opt in self.logic.example_options:
            depends_str = f", depends_on: {opt.depends_on}" if opt.depends_on else ""
            logger.debug(f"  {opt.id}: {opt.display_name}{depends_str}")

    def on_select_changed(self, event: Select.Changed) -> None:
        # Find which row this select belongs to and update corresponding flash button
        grid = self.query_one("#table")
        all_selects = list(grid.query(Select))
        
        # Find index of changed select
        select_index = -1
        for i, select in enumerate(all_selects):
            if select == event.select:
                select_index = i
                break
        
        if select_index >= 0:
            # Calculate which row (each row has 2 selects)
            row_index = select_index // 2
            
            # Get both selects for this row
            lib_select = all_selects[row_index * 2]
            example_select = all_selects[row_index * 2 + 1]
            
            # Get corresponding flash button
            flash_buttons = list(grid.query(Button))
            if row_index < len(flash_buttons):
                flash_button = flash_buttons[row_index]
                
                # Check if both selects have valid values
                lib_selected = lib_select.value is not None and lib_select.value != Select.BLANK
                example_selected = example_select.value is not None and example_select.value != Select.BLANK
                
                # Check dependencies if both are selected
                dependencies_ok = True
                if lib_selected and example_selected:
                    dependencies_ok = self.logic.check_dependencies(lib_select.value, example_select.value)
                    
                    # Log dependency check for debugging
                    example_option = self.logic.get_example_option_by_id(example_select.value)
                    if example_option and example_option.depends_on:
                        lib_option = self.logic.get_lib_option_by_id(lib_select.value)
                        msg_str = f"Dependency check: {example_select.value} requires {example_option.depends_on}, " \
                                f"selected {lib_option.id if lib_option else 'unknown'} -> {'OK' if dependencies_ok else 'FAIL'}"
                        if dependencies_ok:
                            logger.debug(msg_str)
                        else:
                            logger.warning(msg_str)
                
                # Button is enabled only when both are selected AND dependencies are satisfied
                all_conditions_met = lib_selected and example_selected and dependencies_ok
                flash_button.disabled = not all_conditions_met

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reload":
            self.ports = self.logic.find_flash_ports()
            # Reload logic
            self.logic = FlashAppLogic(self.logic.kconfig_path, self.logic.sdkconfig_path, gui_app=self)
            # Ensure all config keys exist after reload
            self._ensure_all_config_keys_exist()
            logger.info("Ports and config reloaded")
            self.refresh(recompose=True)
            
        elif event.button.id and event.button.id.startswith("flash-"):
            port = event.button.id.replace("flash-", "")
            
            # Find corresponding selects for this button
            grid = self.query_one("#table")
            buttons = [btn for btn in grid.query(Button) if btn.id and btn.id.startswith("flash-")]
            
            for i, btn in enumerate(buttons):
                if btn == event.button:
                    # 4 columns now: port, lib, example, flash
                    base_idx = 4 + i * 4  # Skip header row (4 items), then i rows of 4 columns each
                    lib_select = grid.children[base_idx + 1]  # lib is 2nd column (index 1)
                    example_select = grid.children[base_idx + 2]  # example is 3rd column (index 2)
                    
                    # Execute flash sequence using logic and handle result
                    success = self.logic.config_compile_flash(port, lib_select.value, example_select.value)
                    if success:
                        logger.info(f"Flash operation completed successfully for {port}")
                    else:
                        logger.error(f"Flash operation failed for {port}")
                    break


def main():
    parser = argparse.ArgumentParser(description="ESP32 Flash Tool")
    parser.add_argument('-k', '--kconfig', 
                       default="./main/Kconfig.projbuild",
                       help="Path to Kconfig file (default: ./main/Kconfig.projbuild)")
    parser.add_argument('-s', '--sdkconfig',
                       default="./sdkconfig", 
                       help="Path to sdkconfig file (default: ./sdkconfig)")
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Adjust logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    app = FlashAppGui(kconfig_path=args.kconfig, sdkconfig_path=args.sdkconfig)
    app.run()

if __name__ == "__main__":
    main()
