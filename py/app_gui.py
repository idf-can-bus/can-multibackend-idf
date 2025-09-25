# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Textual-based GUI application for ESP32 flash tool.
Provides interactive interface for selecting libraries, examples, and flashing ESP32 devices.
Features real-time compilation output, port detection, and dependency validation.
'''

import logging
import traceback
import os
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.reactive import reactive
from textual.widgets import Static, Button, Select, RichLog, Footer, LoadingIndicator
from py.log.rich_log_extended import RichLogExtended
from .app_logic import FlashApp
from .monitor.shell_monitor_logic import ShellMonitorLogic
from py.log.rich_log_handler import LogSource, RichLogHandler

python_logger = RichLogHandler.get_logger(LogSource.PYTHON)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
)


class AppGui(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #reload {
        background: orange;
        color: black;
    }
    
    #table {
        grid-size: 5;
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
        /*border: solid yellow;  /* Debug: žlutý border kolem tlačítek */
    }
    
    #status {
        width: 100%;
        height: 1fr;
        margin: 1 0;
        border: solid $primary;
    }
    
    .monitor-button {
        background: #2a4a6b;
        color: white;
        text-style: bold;
        height: 3;
    }
    
    .monitor-button:hover {
        background: #3a5a7b;
    }
    
    .monitor-button.active {
        background: #8b2a2a;
        color: white;
        text-style: bold;
        height: 3;
    }
    
    .monitor-button.active:hover {
        background: #9b3a3a;
    }
    
    .flash-button {
        background: #2a6b2a;
        color: white;
        text-style: bold;
        height: 3;
    }
    
    .flash-button:hover {
        background: #3a7b3a;
    }
    
    .flash-button:disabled {
        background: grey;
        text-style: dim;
    }
    
    .flash-button:disabled:hover {
        background: grey;
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
            logging_level: int = logging.DEBUG,
            debug: bool = False,
            use_fake_monitor: bool = False
    ):
        self._debug = debug
        super().__init__()
        

        # Expand user paths
        kconfig_path = os.path.expanduser(kconfig_path)
        sdkconfig_path = os.path.expanduser(sdkconfig_path)
        idf_setup_path = os.path.expanduser(idf_setup_path)

        # Check exitence of all paths, exit if any path does not exist
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

        # Create logic instance with reference to this GUI
        self.logic = FlashApp(
            idf_setup_path, 
            kconfig_path, 
            sdkconfig_path, 
            gui_app=self,
            menu_name="*** CAN bus examples  ***"
        )
        
        # Create monitor GUI logic instance
        self.monitor_logic = ShellMonitorLogic(
            idf_setup_path=idf_setup_path,
            use_fake_monitor=use_fake_monitor
        )

        self.use_fake_monitor = use_fake_monitor

        # Initialize ports
        self.ports, self.real_ports_found = self.logic.find_flash_ports()

    def compose(self) -> ComposeResult:
        # Reloat dosn't work well, so hide it for now
        # yield Button("Reload ports", id="reload")

        with Grid(id="table"):
            # Headers
            yield Static("Port", classes="header")
            yield Static("Library", classes="header")
            yield Static("Example", classes="header")
            yield Static("Flash", classes="header")
            yield Static("Monitor/Log", classes="header")

            # Rows for each port
            for port in self.ports:
                yield Static(port, classes="port")

                # Create lib select - use (display_name, id) format
                lib_choices = [(opt.display_name, opt.id) for opt in self.logic.lib_options]
                print('lib_choices', lib_choices)
                lib_select = Select(lib_choices, prompt="-- Select Lib --")


                # Create example select - use (display_name, id) format  
                example_choices = [(opt.display_name, opt.id) for opt in self.logic.example_options]
                print('example_choices ', example_choices)
                example_select = Select(example_choices, prompt="-- Select Example --")

                flash_button = Button(
                    f"⚡ Flash {port}",
                    id=f"flash-{port}",
                    classes="flash-button",
                    disabled=True
                )
                monitor_button = Button(
                    f"Monitor {port}",  # will be replaced by ShellMonitorLogic
                    id=f"monitor-{port}", 
                    classes="monitor-button",
                    # Some problems with serial monitors was not solved yet (lines vs. chars output).
                    disabled=True  # not (self.use_fake_monitor or self.real_ports_found)
                )
                self.monitor_logic.register_monitor_button(port, monitor_button)

                yield lib_select
                yield example_select
                yield flash_button
                yield monitor_button

        if self._debug:
            yield Button(
                f"RichLogStatistics",
                id=f"richlog-statistics",
                classes="flash-button"                
            )

        # Use RichLogExtended instead of RichLog
        rich_log = RichLogExtended(
            highlight=True, 
            id="status", 
            name="testarea",
            max_lines=2000,        # More lines for long outputs
            buffer_size=20,        # Larger buffer for better performance
            flush_interval=0.05,   # More frequent flushing for responsiveness
            markup=True           # Enable Markup
        )
        yield rich_log

        yield Footer()

    def on_mount(self) -> None:
        # Connect the logging handler to RichLogExtended
        RichLogHandler.set_rich_log(self.query_one(RichLogExtended))

        # Log config file paths and loaded options on startup
        python_logger.info(f"Kconfig: {self.logic.kconfig_path}")
        python_logger.info(f"SDKconfig: {self.logic.sdkconfig_path}")
        python_logger.info(
            f"Loaded {len(self.logic.lib_options)} lib options, {len(self.logic.example_options)} example options")

        # Debug: Print all loaded options
        python_logger.debug("=== LIB OPTIONS ===")
        for opt in self.logic.lib_options:
            python_logger.debug(f"  {opt.id}: {opt.display_name}")

        python_logger.debug("=== EXAMPLE OPTIONS ===")
        for opt in self.logic.example_options:
            depends_str = f", depends_on: {opt.depends_on}" if opt.depends_on else ""
            python_logger.debug(f"  {opt.id}: {opt.display_name}{depends_str}")

    def action_clear_log(self) -> None:
        """Clear the RichLog content"""
        try:
            rich_log = self.query_one(RichLog)
            rich_log.clear()
            python_logger.info("Log cleared")
        except Exception as e:
            python_logger.error(f"Failed to clear log: {e}")

                         
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
            
            # Write message directly to RichLog for immediate display
            # try:
            #     rich_log = self.query_one(RichLog)
            #     rich_log.write(f"INFO: ⏳ {message}")
            #     rich_log.refresh()
            #     # Force app refresh to ensure immediate display
            #     self.refresh()
            # except Exception as e:
            #     python_logger.error(f"Failed to write to RichLog: {e}")
                
        except Exception as e:
            python_logger.error(f"Failed to show loading indicator: {e}")

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
            # Calculate which row (each row has 2 selects: lib and example)
            row_index = select_index // 2

            # Get both selects for this row
            lib_select = all_selects[row_index * 2]
            example_select = all_selects[row_index * 2 + 1]

            # Get corresponding flash button - now we have 4 columns per row
            flash_buttons = [btn for btn in grid.query(Button) if btn.id and btn.id.startswith("flash-")]
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
                        # old code: lib_option = self.logic.get_example_option_by_id(lib_select.value)
                        lib_option = self.logic.get_lib_option_by_id(lib_select.value)
                        msg_str = f"Dependency check: {example_select.value} requires {example_option.depends_on}, " \
                                  f"selected {lib_option.id if lib_option else 'unknown'} -> {'OK' if dependencies_ok else 'FAIL'}"
                        if dependencies_ok:
                            python_logger.debug(msg_str)
                        else:
                            python_logger.warning(msg_str)

                # Button is enabled only when both are selected AND dependencies are satisfied
                all_conditions_met = lib_selected and example_selected and dependencies_ok
                flash_button.disabled = not all_conditions_met

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reload":
            self._on_reload_pressed(event)
        elif event.button.id and event.button.id.startswith("flash-"):
            self._on_flash_pressed(event)
        elif event.button.id and event.button.id.startswith("monitor-"):
            self._on_monitor_pressed(event)
        elif event.button.id == "richlog-statistics":
            self._on_show_stats_pressed(event)

    def _on_reload_pressed(self, event: Button.Pressed) -> None:
        # self.monitor_logic.stop_all_monitors()
        self.ports, self.real_ports_found = self.logic.find_flash_ports()
        # Reload logic
        self.logic.re_init()
        python_logger.info("Ports and config reloaded")
        self.refresh(recompose=True)

    def _on_flash_pressed(self, event: Button.Pressed) -> None:
        port = event.button.id.replace("flash-", "")

        # Find corresponding selects for this button
        grid = self.query_one("#table")
        buttons = [btn for btn in grid.query(Button) if btn.id and btn.id.startswith("flash-")]

        for i, btn in enumerate(buttons):
            if btn == event.button:
                # 4 columns now: port, lib, example, flash
                base_idx = 5 + i * 5  # Skip header row (5 items), then i rows of 5 columns each
                lib_select = grid.children[base_idx + 1]  # lib is 2nd column (index 1)
                example_select = grid.children[base_idx + 2]  # example is 3rd column (index 2)

                # Execute flash sequence asynchronously to keep GUI responsive
                self.run_worker(
                    self.logic.config_compile_flash(port, lib_select.value, example_select.value),
                    name=f"flash_{port}"
                )
                break

    def _on_monitor_pressed(self, event: Button.Pressed) -> None:
        port = event.button.id.replace("monitor-", "")
        
        if self.monitor_logic.is_monitoring(port):
            # Stop monitoring
            if self.monitor_logic.stop_monitor(port):
                serial_logger = RichLogHandler.get_logger(LogSource.SERIAL, port)
                serial_logger.info(f" --- Monitoring stopped on port {port} ---")
        else:
            # Start monitoring
            if self.monitor_logic.start_monitor(port):
                # Get the process and run it asynchronously with cleanup
                self.run_worker(
                    self.monitor_logic.run_monitor_with_cleanup(port),  # ✅ Nová metoda s cleanup
                    name=f"monitor_{port}"
                )

        
    # For debugging purposes, add a button to show statistics
    def _on_show_stats_pressed(self, event: Button.Pressed) -> None:
        """Show RichLogExtended statistics"""
        rich_log = self.query_one(RichLogExtended)
        rich_log.print_stats()