#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Core business logic for ESP32 flash tool application.
Handles configuration updates, code compilation with ESP-IDF, and firmware upload.
Manages the complete workflow from Kconfig parsing to ESP32 flashing.
'''

import glob
import re
from typing import List, Optional, Type, Any
import traceback
import os
import shutil
import time 
import multiprocessing
import psutil

from py.shell_commands import ShellCommandConfig, ShellCommandProcess
from py.config.kconfig_options import ConfigOption, KconfigMenuItems
from py.config.sdkconfig_options import Sdkconfig
from .log.rich_log_handler import LogSource, RichLogHandler

config_logger = RichLogHandler.get_logger(LogSource.CONFIG)
reconfig_logger = RichLogHandler.get_logger(LogSource.RECONFIG)
build_logger = RichLogHandler.get_logger(LogSource.BUILD)
flash_logger = RichLogHandler.get_logger(LogSource.FLASH)

class FlashApp:
    """
    Logic class for ESP32 flash operations
    Handles all business logic separate from GUI
    """

    WORKSPACES_DIR = ".workspaces"

    def __init__(
            self,
            idf_setup_path: str = "~/esp/v5.4.1/esp-idf/export.sh",
            kconfig_path: str = "./main/Kconfig.projbuild",
            sdkconfig_path: str = "./sdkconfig",
            gui_app=None,
            menu_name: str = "*** CAN bus examples  ***",
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.idf_setup_path = idf_setup_path
        self.kconfig_path = kconfig_path
        self.sdkconfig_path = sdkconfig_path
        self.menu_name = menu_name
        self.gui_app = gui_app  # Optional reference to GUI
        self.kconfig_dict = None  # Will be initialized in re_init()
        self.sdkconfig = None  # Will be initialized in re_init()
        self.lib_options = []  # List of ConfigOption for libraries, will be initialized in re_init()
        
        # Compilation monitoring attributes
        self.compilation_process = None
        self.compilation_lib_id = None
        self.compilation_example_id = None

        self.re_init()
        self._workspace_path = sdkconfig_path

    def re_init(self):
        # Load KconfigMenuItems for direct access
        self.kconfig_dict = KconfigMenuItems(self.kconfig_path, self.menu_name)

        # Load sdkconfig
        self.sdkconfig = Sdkconfig(self.sdkconfig_path, self.menu_name)

        # Check for missing CONFIG keys and add them to sdkconfig
        self.sdkconfig.add_no_existing_bool_keys(self.kconfig_dict.get_all_options().keys())

        # # Debug: Print loaded sdkconfig lines
        # print("=== _sdkconfig_lines ===")
        # pprint(self.sdkconfig._sdkconfig_lines)
        # print("=== _keys_to_lines_number ===")
        # pprint(self.sdkconfig._keys_to_lines_number)
        # exit(1)

        # Load configuration options (for backward compatibility)
        self.lib_options, self.example_options = self.load_kconfig_options()

    def get_lib_option_by_id(self, lib_id: str) -> Optional[ConfigOption]:
        """Find lib option by ID using KconfigMenuItems"""
        return self.kconfig_dict.get_option_by_id("Select CAN driver/library", lib_id)

    def get_example_option_by_id(self, example_id: str) -> Optional[ConfigOption]:
        """Find example option by ID using KconfigMenuItems"""
        return self.kconfig_dict.get_option_by_id("Select example", example_id)

    def check_dependencies(self, lib_id: str, example_id: str, prompt_char: str = '✏️') -> bool:
        """Check if selected lib satisfies ALL example dependencies"""
        if not lib_id or not example_id:
            return False

        lib_option = self.get_lib_option_by_id(lib_id)
        example_option = self.get_example_option_by_id(example_id)

        config_logger.debug(f"{prompt_char} lib_id='{lib_id}', lib_option={lib_option}")
        config_logger.debug(f"{prompt_char} example_id='{example_id}', example_option={example_option}")

        if not lib_option or not example_option:
            config_logger.debug(f"{prompt_char} One or both options not found")
            return False

        # If example has no dependencies, it's always compatible
        if not example_option.depends_on:
            config_logger.debug(f"{prompt_char} No dependencies required - compatible")
            return True

        # Check if selected lib ID is in the depends_on list
        if lib_option.id in example_option.depends_on:
            config_logger.debug(f"{prompt_char} {lib_option.id} found in dependencies {example_option.depends_on} -> OK")
            return True
        else:
            config_logger.debug(f"{prompt_char} {lib_option.id} NOT found in dependencies {example_option.depends_on} -> FAIL")
            return False

    def _switch_to_workspace(self, lib_id: str, example_id: str ):
        """
        Switch to workspace
        Copy sdkconfig to workspace if target not exists.
        Can change self._workspace_path to workspace sdkconfig.
        """
        def create_symbolic_link(old_path: str, link_path: str):            
            if not os.path.islink(link_path):
                reconfig_logger.info(f"Create symbolic link from \n{link_path} \nto \n{old_path}")
                os.symlink(old_path, link_path)
        reconfig_logger.info(f"Switching to workspace for lib='{lib_id}' and example='{example_id}'")
        workspace_dir = os.path.join(self.WORKSPACES_DIR, f"{lib_id}_{example_id}")
        workspace_dir = os.path.realpath(os.path.expanduser(workspace_dir))
        if not os.path.exists(workspace_dir):
            os.makedirs(workspace_dir)
        # Create symbolic links to all source directories in not already exists and is not have a special name.
        link_list = [x for x in os.listdir(".") if os.path.isdir(x) and x!='build' and (not x.startswith('.'))]
        link_list.append("CMakeLists.txt")
        for item in link_list:
            abs_old_path = os.path.abspath(f"./{item}")
            abs_link_path = os.path.abspath(f"{workspace_dir}/{item}")
            create_symbolic_link(abs_old_path, abs_link_path)
        # Copy sdkconfig to workspace if target not exists
        if not os.path.exists(f"{workspace_dir}/sdkconfig"):
            shutil.copy(self.sdkconfig_path, f"{workspace_dir}/sdkconfig")
        else:
            # Reload sdkconfig from workspace
            self.sdkconfig = Sdkconfig(f"{workspace_dir}/sdkconfig", self.menu_name)
        self._workspace_path = workspace_dir
        reconfig_logger.info(f"Switched to workspace: {workspace_dir}")
        return True


    def _update_sdkconfig(self, lib_id: str, example_id: str ):
        """Update sdkconfig using new Sdkconfig classes"""
        try:
            reconfig_logger.info(f"Consider to update sdkconfig for lib='{lib_id}' and example='{example_id}'")

            # Step 1: Get all config option IDs from KconfigMenuItems
            all_options = self.kconfig_dict.get_all_options()
            config_ids = list(all_options.keys())
            reconfig_logger.debug(f"Found {len(config_ids)} config options: {config_ids}")

            # Step 2: Find relevant SdkconfigLines for these IDs
            relevant_lines = {}
            for config_id in config_ids:
                line = self.sdkconfig.get_line_by_key(config_id)
                if line:
                    relevant_lines[config_id] = line
                    config_logger.debug(f"Found existing line for {config_id}: {line.value}")
                else:
                    config_logger.debug(
                        f"Config {config_id} not found in sdkconfig (should have been added during initialization)")

            # Step 3: Set values based on selections
            changes_made = 0
            for config_id, line in relevant_lines.items():
                new_value = None

                # Determine new value based on selection
                if config_id == lib_id:
                    new_value = 'y'
                    reconfig_logger.info(f"ENABLE: {config_id} (selected lib)")
                elif config_id == example_id:
                    new_value = 'y'
                    reconfig_logger.info(f"ENABLE: {config_id} (selected example)")
                else:
                    new_value = 'n'
                    reconfig_logger.debug(f"DISABLE: {config_id} (not selected)")

                # Update line if value changed
                reconfig_logger.info(f"Consider to change {config_id}: '{line.value}' -> '{new_value}'")
                if line.value != new_value:
                    line.set_value(new_value)
                    changes_made += 1
                    reconfig_logger.debug(f"Changed {config_id}: {line.value} -> {new_value}")

            # Step 4: Write sdkconfig if any changes were made
            if changes_made > 0:
                reconfig_logger.info(f"Writing sdkconfig with {changes_made} changes")
                self.sdkconfig.set_sdkconfig_path(f'{self._workspace_path}/sdkconfig')
                self.sdkconfig.write()                
            else:
                reconfig_logger.info("No changes needed in sdkconfig")

            return True

        except Exception as e:
            config_logger.error(f"Failed to update sdkconfig: {e}")
            config_logger.info(traceback.format_exc())
            return False


    async def call_with_results(
        self, target: ShellCommandConfig | Type[Any], 
        name: str, logger: RichLogHandler, 
        *args, **kwargs) -> bool:
        """
        Call a target function or class with arguments and log results.
        :param target: Function or class to call.
        :param name: Name of the operation.
        :param logger: Logger instance to use.
        :param args: Arguments to pass to the target.
        :param kwargs: Keyword arguments to pass to the target.
        :return: True if successful, False otherwise.
        """ 
        def log_start():
            logger.info(f"--- {name} starts 🚀 ---\n") 
        
        def log_success(success: bool):
            if success:
                logger.info(f"=== {name} completed ✅ ===") 
            else:
                logger.error(f"!!! {name} failed ❌ !!!") 

        try:
            if isinstance(target, ShellCommandConfig):
                # run asynchrounously
                process = ShellCommandProcess(config=target, logger=logger)
                log_start()
                success = await process.run_end_wait()
                log_success(success)
                return success
            elif callable(target):
                # run synchronously python function/method
                result = target(*args, **kwargs)
                if isinstance(result, bool):
                    log_success(result)
                    return result
                else:
                    log_success(True)
                return True
            else:
                raise TypeError("First argument must be ShellCommandConfig or a function.")
        except Exception as e:
            logger.error(f"!!! {name} failed ❌: {e} !!!")
            logger.info(traceback.format_exc())
            return False
        

    async def config_compile_flash(self, port: str, lib_id: str, example_id: str) -> bool:
        """
        Execute complete flash sequence: switch to workspace,update config, compile, upload
        Returns True if all steps successful, False if any step fails
        """

        # Step 0: Switch to workspace
        success0 = await self.call_with_results(
            target=self._switch_to_workspace,
            name="Switch to workspace",
            logger=reconfig_logger,
            lib_id=lib_id, example_id=example_id
        )
        if not success0:
            return False


        # python_logger.info(f"config_compile_flash")
        # Step 1: Update sdkconfig
        success1 = await self.call_with_results(
            target=self._update_sdkconfig, 
            name="Update sdkconfig", 
            logger=reconfig_logger, 
            lib_id=lib_id, example_id=example_id
        )
        # python_logger.info(f"Step 1: Update sdkconfig success1={success1}")
        if not success1:
            return False

        # Step 2: Run building asynchronously
        jobs = self.get_optimal_jobs()
        should_fullclean = self.should_fullclean(None, None)  # TODO: add old and new config
        if should_fullclean:
            command = f"bash -c 'export MAKEFLAGS=-j{jobs} && source {self.idf_setup_path} && cd {self._workspace_path} && idf.py fullclean && idf.py build'"
        else:
            command=f"bash -c 'export MAKEFLAGS=-j{jobs} && source {self.idf_setup_path} && cd {self._workspace_path} && idf.py build '"
        success2 = await self.call_with_results(
            name="Compile ESP32 firmware",
            target=ShellCommandConfig(
                name="Compile ESP32 firmware",  
                command=command
            ), 
            logger=build_logger, 
        )
        # build_logger.info(f"\nStep 2: Compile ESP32 firmware success2={success2}\n")
        if not success2:
            return False

        # Step 3: Flash firmware
        time.sleep(0.5) # wait for build to finish
        command = f"bash -c 'source {self.idf_setup_path} && cd {self._workspace_path} && idf.py -p /dev/{port} flash'"
        success3 = await self.call_with_results(
            name=f"Flash firmware to /dev/{port}",
            target=ShellCommandConfig(
                name=f"Flash firmware to /dev/{port}", 
                command=command
            ), 
            logger=flash_logger, 
        )
        #  flash_logger.info(f"\nStep 3: Flash firmware to /dev/{port} success3={success3}\n")
        return success3

    
    def find_flash_ports(self, default_ports: list[str] = ['Port1', 'Port2', 'Port3', 'Port4']) -> tuple[list[str], bool]:
        """Find available flash ports"""
        real_ports_found = False
        ports = glob.glob('/dev/ttyACM*')
        flash_ports1 = sorted(p[5:] for p in ports if re.match(r'/dev/ttyACM\d+$', p))
        ports = glob.glob('/dev/ttyUSB*')
        flash_ports2 = sorted(p[5:] for p in ports if re.match(r'/dev/ttyUSB\d+$', p))
        flash_ports = flash_ports1 + flash_ports2
        if not flash_ports:
            return default_ports, real_ports_found
        else:
            real_ports_found = True
            return flash_ports, real_ports_found

    def load_kconfig_options(self) -> tuple[List[ConfigOption], List[ConfigOption]]:
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

    @staticmethod
    def get_optimal_jobs() -> int:
        """Get optimal number of parallel jobs for idf.py build"""
        
        # Get CPU count
        cpu_count = multiprocessing.cpu_count()
        
        # Get available memory (GB)
        available_memory = psutil.virtual_memory().available / (1024**3)
        
        # Calculate optimal jobs based on CPU and memory
        # ESP32 compilation is memory-intensive
        if available_memory < 4:
            # Low memory - be conservative
            jobs = max(1, cpu_count - 2)
        elif available_memory < 8:
            # Medium memory
            jobs = max(1, cpu_count - 1)
        else:
            # High memory - can use more cores
            jobs = cpu_count
        
        # Ensure minimum and maximum bounds
        jobs = max(1, min(jobs, 16))  # Max 16 jobs
        
        return jobs

    def should_fullclean(self, old_config: dict, new_config: dict) -> bool:
        """Determine if full clean is needed based on config changes"""
        # TODO: implement this, must thing about original dir and new dir in workspace
        # # Critical changes that require full rebuild
        # critical_keys = [
        #     'CONFIG_IDF_TARGET',           # Target chip change
        #     'CONFIG_COMPILER_OPTIMIZATION', # Optimization level
        #     'CONFIG_ESP_SYSTEM_SINGLE_CORE', # Single/dual core
        #     'CONFIG_FREERTOS_HZ',          # RTOS frequency
        # ]
        
        # # Check if any critical config changed
        # for key in critical_keys:
        #     if old_config.get(key) != new_config.get(key):
        #         return True
        
        # # CAN backend changes might need full rebuild
        # can_backend_keys = [k for k in old_config.keys() if 'CAN_BACKEND' in k]
        # for key in can_backend_keys:
        #     if old_config.get(key) != new_config.get(key):
        #         return True
        
        return False