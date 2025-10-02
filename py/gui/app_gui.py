# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Textual-based GUI application for ESP32 flash tool.
Provides interactive interface for selecting libraries, examples, and flashing ESP32 devices.
Features real-time compilation output, port detection, and dependency validation.
'''

import asyncio
import logging
import os
import time

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Button, Footer, TabbedContent, TabPane
from py.app_logic import FlashApp
from py.monitor.shell_monitor_logic import ShellMonitorLogic
from py.log.rich_log_handler import LogSource, RichLogHandler
from py.gui.build_flash_tab import BuildFlashTab
from py.gui.serial_monitor_tab import SerialMonitorsTab

python_logger = RichLogHandler.get_logger(LogSource.PYTHON)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
)


class AppGui(App):
    CSS_PATH = ["css/app.css", "css/build_flash_tab.css", "css/serial_monitor_tab.css"]
    
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    ports = reactive(list)

    def __init__(
            self,
            kconfig_path: str = "./main/Kconfig.projbuild",
            sdkconfig_path: str = "./sdkconfig",
            idf_setup_path: str = "~/esp/v5.4.1/esp-idf/export.sh",
            debug: bool = False
    ):
        """
        Initialize ESP32 Flash Tool GUI application.
        
        Args:
            kconfig_path: Path to Kconfig.projbuild file
            sdkconfig_path: Path to sdkconfig file
            idf_setup_path: Path to ESP-IDF setup script
            debug: Enable debug features in GUI
        """
        self._debug = debug
        super().__init__()
        kconfig_path = os.path.expanduser(kconfig_path)
        sdkconfig_path = os.path.expanduser(sdkconfig_path)
        idf_setup_path = os.path.expanduser(idf_setup_path)
        if not os.path.exists(kconfig_path):
            python_logger.error(f"Kconfig file not found at: '{kconfig_path}'")
            exit(1)
        if not os.path.exists(sdkconfig_path):
            python_logger.error(f"SDKconfig file not found at: '{sdkconfig_path}'")
            exit(1)
        if not os.path.exists(idf_setup_path):
            python_logger.error(f"ESP-IDF setup script not found at: '{idf_setup_path}'")
            exit(1)

        self.kconfig_path = kconfig_path
        self.sdkconfig_path = sdkconfig_path
        self.idf_setup_path = os.path.expanduser(idf_setup_path)
        self.logic = FlashApp(
            idf_setup_path, 
            kconfig_path, 
            sdkconfig_path, 
            gui_app=self,
            menu_name="*** CAN bus examples  ***"
        )
        self.monitor_logic = ShellMonitorLogic(
            idf_setup_path=idf_setup_path,
            read_timeout=0.01,
            write_timeout=0.01,
            buffer_size=0
        )
        self.ports, self.real_ports_found = self.logic.find_flash_ports()

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Build & Flash"):
                yield BuildFlashTab(
                    logic=self.logic, 
                    gui_app=self,
                    ports=self.ports, 
                    python_logger=python_logger,
                    debug=self._debug
                )
            with TabPane("Serial Monitors"):
                yield SerialMonitorsTab(
                    self.ports, python_logger, self.monitor_logic, max_log_lines=500
                )

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button events from main window."""
        pass

    async def action_quit(self) -> None:
        """
        Quit application gracefully.
        Stops all active monitor processes before shutting down to prevent subprocess errors.
        """
        try:
            stopped_count = await self.monitor_logic.stop_all_monitors()
            if stopped_count > 0:
                python_logger.info(f"Stopped {stopped_count} active monitor process(es) before quitting")
            await asyncio.sleep(0.2)
        except Exception as e:
            python_logger.error(f"Error stopping monitor processes: {e}")
        finally:
            self.exit()
