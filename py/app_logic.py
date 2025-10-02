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
from typing import List, Optional, Type, Any, Tuple
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
        """
        Initialize flash application logic.
        
        Args:
            idf_setup_path: Path to ESP-IDF environment setup script
            kconfig_path: Path to Kconfig.projbuild file
            sdkconfig_path: Path to sdkconfig file
            gui_app: Optional reference to GUI application instance
            menu_name: Menu name in Kconfig to parse
        """
        super().__init__(*args, **kwargs)
        self.idf_setup_path = idf_setup_path
        self.kconfig_path = kconfig_path
        self.sdkconfig_path = sdkconfig_path
        self.menu_name = menu_name
        self.gui_app = gui_app
        self.kconfig_dict = None
        self.sdkconfig = None
        self.lib_options = []
        
        self.compilation_process = None
        self.compilation_lib_id = None
        self.compilation_example_id = None

        self.re_init()
        self._workspace_path = sdkconfig_path

    def re_init(self):
        """Reload configuration from Kconfig and sdkconfig files."""
        self.kconfig_dict = KconfigMenuItems(self.kconfig_path, self.menu_name)
        self.sdkconfig = Sdkconfig(self.sdkconfig_path, self.menu_name)
        self.sdkconfig.add_no_existing_bool_keys(self.kconfig_dict.get_all_options().keys())
        self.lib_options, self.example_options = self.load_kconfig_options()

    def get_lib_option_by_id(self, lib_id: str) -> Optional[ConfigOption]:
        """Find library option by ID."""
        return self.kconfig_dict.get_option_by_id("Select CAN driver/library", lib_id)

    def get_example_option_by_id(self, example_id: str) -> Optional[ConfigOption]:
        """Find example option by ID."""
        return self.kconfig_dict.get_option_by_id("Select example", example_id)

    def check_dependencies(self, lib_id: str, example_id: str, prompt_char: str = '✏️') -> bool:
        """
        Check if selected library satisfies example dependencies.
        
        Args:
            lib_id: Library configuration ID
            example_id: Example configuration ID
            prompt_char: Character for log prompts
            
        Returns:
            True if dependencies are satisfied, False otherwise
        """
        if not lib_id or not example_id:
            return False

        lib_option = self.get_lib_option_by_id(lib_id)
        example_option = self.get_example_option_by_id(example_id)

        config_logger.debug(f"{prompt_char} lib_id='{lib_id}', lib_option={lib_option}")
        config_logger.debug(f"{prompt_char} example_id='{example_id}', example_option={example_option}")

        if not lib_option or not example_option:
            config_logger.debug(f"{prompt_char} One or both options not found")
            return False
        if not example_option.depends_on:
            config_logger.debug(f"{prompt_char} No dependencies required - compatible")
            return True
        if lib_option.id in example_option.depends_on:
            config_logger.debug(
                f"{prompt_char} {lib_option.id} found in dependencies "
                f"{example_option.depends_on} -> OK"
            )
            return True
        else:
            config_logger.debug(
                f"{prompt_char} {lib_option.id} NOT found in dependencies "
                f"{example_option.depends_on} -> FAIL"
            )
            return False

    def _switch_to_workspace(self, lib_id: str, example_id: str):
        """
        Switch to isolated workspace directory for lib/example combination.
        Creates symbolic links to source directories and copies sdkconfig if needed.
        Updates self._workspace_path to workspace directory.
        
        Args:
            lib_id: Library configuration ID
            example_id: Example configuration ID
            
        Returns:
            True on success
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
        link_list = [x for x in os.listdir(".") if os.path.isdir(x) and x != 'build' and (not x.startswith('.'))]
        link_list.append("CMakeLists.txt")
        for item in link_list:
            abs_old_path = os.path.abspath(f"./{item}")
            abs_link_path = os.path.abspath(f"{workspace_dir}/{item}")
            create_symbolic_link(abs_old_path, abs_link_path)
        if not os.path.exists(f"{workspace_dir}/sdkconfig"):
            shutil.copy(self.sdkconfig_path, f"{workspace_dir}/sdkconfig")
        else:
            self.sdkconfig = Sdkconfig(f"{workspace_dir}/sdkconfig", self.menu_name)
        self._workspace_path = workspace_dir
        reconfig_logger.info(f"Switched to workspace: {workspace_dir}")
        return True

    def _update_sdkconfig(self, lib_id: str, example_id: str):
        """
        Update sdkconfig file based on selected library and example.
        Enables selected options and disables all others.
        
        Args:
            lib_id: Library configuration ID to enable
            example_id: Example configuration ID to enable
            
        Returns:
            True on success, False on error
        """
        try:
            reconfig_logger.info(f"Consider to update sdkconfig for lib='{lib_id}' and example='{example_id}'")
            all_options = self.kconfig_dict.get_all_options()
            config_ids = list(all_options.keys())
            reconfig_logger.debug(f"Found {len(config_ids)} config options: {config_ids}")
            relevant_lines = {}
            for config_id in config_ids:
                line = self.sdkconfig.get_line_by_key(config_id)
                if line:
                    relevant_lines[config_id] = line
                    config_logger.debug(f"Found existing line for {config_id}: {line.value}")
                else:
                    config_logger.debug(f"Config {config_id} not found in sdkconfig")
            changes_made = 0
            for config_id, line in relevant_lines.items():
                if config_id == lib_id:
                    new_value = 'y'
                    reconfig_logger.info(f"ENABLE: {config_id} (selected lib)")
                elif config_id == example_id:
                    new_value = 'y'
                    reconfig_logger.info(f"ENABLE: {config_id} (selected example)")
                else:
                    new_value = 'n'
                    reconfig_logger.debug(f"DISABLE: {config_id} (not selected)")
                reconfig_logger.info(f"Consider to change {config_id}: '{line.value}' -> '{new_value}'")
                if line.value != new_value:
                    line.set_value(new_value)
                    changes_made += 1
                    reconfig_logger.debug(f"Changed {config_id}: {line.value} -> {new_value}")
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
        Execute shell command or Python function with logging.
        
        Args:
            target: ShellCommandConfig or callable to execute
            name: Operation name for logging
            logger: Logger instance
            *args: Arguments for callable
            **kwargs: Keyword arguments for callable
            
        Returns:
            True on success, False on failure
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
                process = ShellCommandProcess(config=target, logger=logger)
                log_start()
                success = await process.run_end_wait()
                log_success(success)
                return success
            elif callable(target):
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
        Execute complete build and flash workflow.
        1. Switch to workspace
        2. Update sdkconfig
        3. Compile firmware
        4. Flash to device
        
        Args:
            port: Serial port identifier
            lib_id: Library configuration ID
            example_id: Example configuration ID
            
        Returns:
            True if all steps successful, False if any step fails
        """
        success0 = await self.call_with_results(
            target=self._switch_to_workspace,
            name="Switch to workspace",
            logger=reconfig_logger,
            lib_id=lib_id, example_id=example_id
        )
        if not success0:
            return False
        success1 = await self.call_with_results(
            target=self._update_sdkconfig, 
            name="Update sdkconfig", 
            logger=reconfig_logger, 
            lib_id=lib_id, example_id=example_id
        )
        if not success1:
            return False
        jobs = self.get_optimal_jobs()
        should_fullclean = self.should_fullclean(None, None)
        if should_fullclean:
            command = (
                f"bash -c 'export MAKEFLAGS=-j{jobs} && "
                f"source {self.idf_setup_path} && "
                f"cd {self._workspace_path} && "
                f"idf.py fullclean && idf.py build'"
            )
        else:
            command = (
                f"bash -c 'export MAKEFLAGS=-j{jobs} && "
                f"source {self.idf_setup_path} && "
                f"cd {self._workspace_path} && "
                f"idf.py build'"
            )
        success2 = await self.call_with_results(
            name="Compile ESP32 firmware",
            target=ShellCommandConfig(
                name="Compile ESP32 firmware",  
                command=command
            ), 
            logger=build_logger, 
        )
        if not success2:
            return False

        time.sleep(0.5)
        command = f"bash -c 'source {self.idf_setup_path} && cd {self._workspace_path} && idf.py -p /dev/{port} flash'"
        success3 = await self.call_with_results(
            name=f"Flash firmware to /dev/{port}",
            target=ShellCommandConfig(
                name=f"Flash firmware to /dev/{port}", 
                command=command
            ), 
            logger=flash_logger, 
        )
        return success3

    def find_flash_ports(self, default_ports: List[str] = None) -> Tuple[List[str], bool]:
        """
        Detect available ESP32 serial ports.
        
        Args:
            default_ports: Fake ports to use if no real ports found
            
        Returns:
            Tuple of (port_list, real_ports_found_flag)
        """
        if default_ports is None:
            default_ports = ['Port1', 'Port2', 'Port3', 'Port4']
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
        """
        Load library and example options from Kconfig file.
        
        Returns:
            Tuple of (lib_options, example_options)
        """
        lib_menu = "Select CAN driver/library"
        lib_options = []
        if lib_menu in self.kconfig_dict._menus_dict:
            for option in self.kconfig_dict._menus_dict[lib_menu].values():
                lib_options.append(ConfigOption(
                    id=option.id,
                    display_name=option.display_name,
                    config_type=option.config_type,
                    depends_on=option.depends_on
                ))  
        example_menu = "Select example"
        example_options = []
        if example_menu in self.kconfig_dict._menus_dict:
            for option in self.kconfig_dict._menus_dict[example_menu].values():
                example_options.append(ConfigOption(
                    id=option.id,
                    display_name=option.display_name,
                    config_type=option.config_type,
                    depends_on=option.depends_on
                ))

        return lib_options, example_options 

    @staticmethod
    def get_optimal_jobs() -> int:
        """
        Calculate optimal number of parallel compilation jobs.
        Based on CPU count and available memory.
        
        Returns:
            Number of parallel jobs (1-16)
        """
        cpu_count = multiprocessing.cpu_count()
        available_memory = psutil.virtual_memory().available / (1024**3)
        if available_memory < 4:
            jobs = max(1, cpu_count - 2)
        elif available_memory < 8:
            jobs = max(1, cpu_count - 1)
        else:
            jobs = cpu_count
        
        jobs = max(1, min(jobs, 16))
        
        return jobs

    def should_fullclean(self, old_config: dict = None, new_config: dict = None) -> bool:
        """
        Determine if full clean build is needed.
        Currently always returns False - incremental builds only.
        
        Args:
            old_config: Previous configuration (unused)
            new_config: New configuration (unused)
            
        Returns:
            False (incremental builds only)
        """
        return False
