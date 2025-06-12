# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Textual-based GUI application for ESP32 flash tool.
Provides interactive interface for selecting libraries, examples, and flashing ESP32 devices.
Features real-time compilation output, port detection, and dependency validation.
'''

import logging
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Static, Button, Select, RichLog, Footer, LoadingIndicator
import os
from .flash_app_logic import FlashAppLogic
from .rich_log_handler import RichLogHandler

# Configure logging with custom handler
logger = logging.getLogger(__name__)
rich_log_handler = RichLogHandler()
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s',
    handlers=[rich_log_handler]
)

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
        ("ctrl+l", "clear_log", "Clear Log"),
    ]

    ports = reactive(list)

    def __init__(
            self,
            kconfig_path: str = "./main/Kconfig.projbuild",
            sdkconfig_path: str = "./sdkconfig",
            idf_setup_path: str = "~/esp/v5.4.1/esp-idf/export.sh",
            logging_level: int = logging.DEBUG
    ):
        super().__init__()

        # Expand user paths
        kconfig_path = os.path.expanduser(kconfig_path)
        sdkconfig_path = os.path.expanduser(sdkconfig_path)
        idf_setup_path = os.path.expanduser(idf_setup_path)

        # Check exitence of all paths, exit if any path does not exist
        if not os.path.exists(kconfig_path):
            logger.error(f"Kconfig file not found at: '{kconfig_path}'")
            exit(1)
        if not os.path.exists(sdkconfig_path):
            logger.error(f"SDKconfig file not found at: '{sdkconfig_path}'")
            exit(1)
        if not os.path.exists(idf_setup_path):
            logger.error(f"ESP-IDF setup script not found at: '{idf_setup_path}'")
            exit(1)

        self.kconfig_path = kconfig_path
        self.sdkconfig_path = sdkconfig_path
        self.idf_setup_path = os.path.expanduser(idf_setup_path)

        # Create logic instance with reference to this GUI
        self.logic = FlashAppLogic(idf_setup_path, kconfig_path, sdkconfig_path, gui_app=self,
                                   menu_name="*** Example to build ***")

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
        logger.info(
            f"Loaded {len(self.logic.lib_options)} lib options, {len(self.logic.example_options)} example options")

        # Debug: Print all loaded options
        logger.debug("=== LIB OPTIONS ===")
        for opt in self.logic.lib_options:
            logger.debug(f"  {opt.id}: {opt.display_name}")

        logger.debug("=== EXAMPLE OPTIONS ===")
        for opt in self.logic.example_options:
            depends_str = f", depends_on: {opt.depends_on}" if opt.depends_on else ""
            logger.debug(f"  {opt.id}: {opt.display_name}{depends_str}")

    def action_clear_log(self) -> None:
        """Clear the RichLog content"""
        try:
            rich_log = self.query_one(RichLog)
            rich_log.clear()
            logger.info("Log cleared")
        except Exception as e:
            logger.error(f"Failed to clear log: {e}")

    def show_loading(self, message: str = "Compiling...") -> None:
        """Show loading indicator with message"""
        try:
            # Try to find existing loading indicator
            try:
                loading = self.query_one(LoadingIndicator)
                loading.remove()
            except:
                pass
            
            # Create new loading indicator
            loading = LoadingIndicator()
            loading.id = "compilation_loading"
            
            # Mount it to the app
            self.mount(loading)
            
            # Log the message
            logger.info(f"⏳ {message}")
            
            # Force refresh of RichLog
            try:
                rich_log = self.query_one(RichLog)
                rich_log.refresh()
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to show loading indicator: {e}")

    def hide_loading(self) -> None:
        """Hide loading indicator"""
        try:
            loading = self.query_one("#compilation_loading")
            loading.remove()
        except:
            pass

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
            self.logic.re_init()
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