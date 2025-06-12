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
import logging
import os
import pty
import re
import select
import subprocess
import threading
import time
from typing import List, Optional

from .kconfig_option import ConfigOption, KconfigMenuItems
from .sdkconfig import Sdkconfig

logger = logging.getLogger(__name__)


class FlashAppLogic:
    """
    Logic class for ESP32 flash operations
    Handles all business logic separate from GUI
    """

    def __init__(
            self,
            idf_setup_path: str = "~/esp/v5.4.1/esp-idf/export.sh",
            kconfig_path: str = "./main/Kconfig.projbuild",
            sdkconfig_path: str = "./sdkconfig",
            gui_app=None,
            menu_name: str = "*** Example to build ***"
    ):
        self.idf_setup_path = idf_setup_path
        self.kconfig_path = kconfig_path
        self.sdkconfig_path = sdkconfig_path
        self.menu_name = menu_name
        self.gui_app = gui_app  # Optional reference to GUI
        self.kconfig_dict = None  # Will be initialized in re_init()
        self.sdkconfig = None  # Will be initialized in re_init()
        self.lib_options = []  # List of ConfigOption for libraries, will be initialized in re_init()
        self.re_init()

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
                    logger.debug(
                        f"Config {config_id} not found in sdkconfig (should have been added during initialization)")

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

    def compile_code(self, lib_id: str, example_id: str) -> bool:
        """Compile the C/C++ code for selected configuration"""
        process = None
        try:
            logger.info(f"Starting compilation for {lib_id}/{example_id}")
            
            # Show loading indicator if GUI is available
            if self.gui_app:
                self.gui_app.show_loading(f"=== Compiling {lib_id}/{example_id}...")
            
            # Prepare the command that sources ESP-IDF environment and runs idf.py all
            # Using bash -c to execute both source and idf.py in the same shell
            cmd = f'bash -c "source {self.idf_setup_path} && idf.py all"'
            logger.info(f"Executing: {cmd}")
            
            # Force refresh of RichLog before starting process
            if self.gui_app:
                try:
                    rich_log = self.gui_app.query_one("RichLog")
                    rich_log.refresh()
                    time.sleep(0.2)
                except:
                    pass
            
            # Ensure log directory exists
            os.makedirs(os.path.dirname(os.path.abspath("compile.log.txt")), exist_ok=True)
            
            # Open log files
            with open("compile.log.txt", "w", encoding="utf-8") as log_file, \
                 open("compile.err.txt", "w", encoding="utf-8") as err_file:
                
                # Write headers to log files
                log_file.write(f"=== ESP32 Compilation Log ===\n")
                log_file.write(f"Library: {lib_id}\n")
                log_file.write(f"Example: {example_id}\n")
                log_file.write(f"Command: {cmd}\n")
                log_file.write(f"{'='*50}\n\n")
                log_file.flush()
                
                err_file.write(f"=== ESP32 Compilation Errors ===\n")
                err_file.write(f"Library: {lib_id}\n")
                err_file.write(f"Example: {example_id}\n")
                err_file.write(f"Command: {cmd}\n")
                err_file.write(f"{'='*50}\n\n")
                err_file.flush()
                
                # Use pty for unbuffered output - better real-time streaming
                master_fd, slave_fd = pty.openpty()
                
                try:
                    # Start the process with pty for unbuffered output
                    process = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=slave_fd,
                        stderr=subprocess.STDOUT,  # Merge stderr to stdout for simplicity
                        universal_newlines=True,
                        preexec_fn=os.setsid,  # Create new process group for easier termination
                        env=dict(os.environ, PYTHONUNBUFFERED='1')  # Force unbuffered Python output
                    )
                    
                    # Close slave fd in parent process
                    os.close(slave_fd)
                    
                    # Function to read from master fd and log in real-time
                    def read_output():
                        try:
                            buffer = ""
                            while True:
                                # Use select to check if data is available (non-blocking)
                                ready, _, _ = select.select([master_fd], [], [], 0.1)
                                if ready:
                                    try:
                                        data = os.read(master_fd, 1024).decode('utf-8', errors='replace')
                                        if not data:
                                            break
                                        
                                        buffer += data
                                        
                                        # Process complete lines
                                        while '\n' in buffer:
                                            line, buffer = buffer.split('\n', 1)
                                            if line.strip():  # Only log non-empty lines
                                                # Determine if it's error or info based on content
                                                if any(keyword in line.lower() for keyword in ['error', 'failed', 'fatal']):
                                                    logger.error(f"COMPILE: {line}")
                                                    err_file.write(f"{line}\n")
                                                    err_file.flush()
                                                elif any(keyword in line.lower() for keyword in ['warning', 'warn']):
                                                    logger.warning(f"COMPILE: {line}")
                                                    log_file.write(f"{line}\n")
                                                    log_file.flush()
                                                else:
                                                    logger.info(f"COMPILE: {line}")
                                                    log_file.write(f"{line}\n")
                                                    log_file.flush()
                                    except OSError:
                                        # Master fd closed
                                        break
                                else:
                                    # Check if process is still running
                                    if process.poll() is not None:
                                        # Process finished, read any remaining data
                                        try:
                                            remaining_data = os.read(master_fd, 4096).decode('utf-8', errors='replace')
                                            if remaining_data:
                                                buffer += remaining_data
                                                # Process remaining lines
                                                lines = buffer.split('\n')
                                                for line in lines[:-1]:  # All but last (might be incomplete)
                                                    if line.strip():
                                                        logger.info(f"COMPILE: {line}")
                                                        log_file.write(f"{line}\n")
                                                        log_file.flush()
                                        except OSError:
                                            pass
                                        break
                                    
                        except Exception as e:
                            logger.error(f"Error reading output: {e}")
                    
                    # Start thread to read output in real-time
                    output_thread = threading.Thread(target=read_output)
                    output_thread.daemon = True
                    output_thread.start()
                    
                    # Wait for process to complete with timeout (5 minutes)
                    start_time = time.time()
                    timeout = 300  # 5 minutes
                    
                    while True:
                        return_code = process.poll()
                        if return_code is not None:
                            break
                            
                        if time.time() - start_time > timeout:
                            logger.error("Compilation timed out after 5 minutes")
                            # Kill the entire process group
                            try:
                                os.killpg(os.getpgid(process.pid), 9)
                            except:
                                process.kill()
                            return False
                            
                        time.sleep(0.1)  # Small sleep to prevent busy waiting
                    
                    # Wait for output thread to finish reading (with timeout)
                    output_thread.join(timeout=5)
                    
                finally:
                    # Clean up file descriptors
                    try:
                        os.close(master_fd)
                    except:
                        pass
                
                # Write summary to log files
                log_file.write(f"\n{'='*50}\n")
                log_file.write(f"Compilation finished with return code: {return_code}\n")
                log_file.flush()
                
                err_file.write(f"\n{'='*50}\n")
                err_file.write(f"Compilation finished with return code: {return_code}\n")
                err_file.flush()
                
                # Check compilation result
                if return_code == 0:
                    logger.info("Compilation completed successfully")
                    # Hide loading indicator
                    if self.gui_app:
                        self.gui_app.hide_loading()
                    return True
                else:
                    logger.error(f"Compilation failed with return code: {return_code}")
                    # Hide loading indicator
                    if self.gui_app:
                        self.gui_app.hide_loading()
                    return False
                    
        except Exception as e:
            logger.error(f"Compilation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Hide loading indicator on error
            if self.gui_app:
                self.gui_app.hide_loading()
            if process:
                try:
                    process.terminate()
                except:
                    pass
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
        if not self.compile_code(lib_id, example_id):
            logger.error("Flash sequence aborted: compilation failed")
            return False

        # Step 3: Upload to ESP32
        if not self.upload_to_port(port, lib_id, example_id):
            logger.error("Flash sequence aborted: upload failed")
            return False

        return True

    @staticmethod
    def find_flash_ports(default_ports: list[str] = ['Port1', 'Port2', 'Port3', 'Port4']):
        """Find available flash ports"""
        ports = glob.glob('/dev/ttyACM*')
        flash_ports1 = sorted(p[5:] for p in ports if re.match(r'/dev/ttyACM\d+$', p))
        ports = glob.glob('/dev/ttyUSB*')
        flash_ports2 = sorted(p[5:] for p in ports if re.match(r'/dev/ttyUSB\d+$', p))
        flash_ports = flash_ports1 + flash_ports2
        if not flash_ports:
            return default_ports
        else:
            return flash_ports

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