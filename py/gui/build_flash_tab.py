# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Build and flash tab for ESP32 Flash Tool GUI.
Provides interface for selecting libraries, examples, and flashing firmware to multiple ESP32 ports.
Includes real-time build output logging and dependency validation.
'''
from typing import List
from textual.app import App, ComposeResult
from textual.containers import Grid, Container
from textual.widgets import Static, Button, Select
from py.log.rich_log_extended import RichLogExtended
from py.app_logic import FlashApp
from py.log.rich_log_handler import RichLogHandler


class BuildFlashTab(Container):
    """
    Build and flash operations tab.
    Contains configuration table for library/example selection per port,
    comprehensive build/flash log output, and toolbar with utility functions.
    """

    def __init__(
            self, 
            logic: FlashApp,
            gui_app: App,
            ports: List[str],
            python_logger: RichLogHandler,
            debug: bool = False
        ) -> None:
        super().__init__(id="build-flash-tab")
        self.ports = ports
        self.logic = logic
        self.gui_app = gui_app
        self.python_logger = python_logger
        self._debug = debug

    def _build_table(self) -> ComposeResult:
        """Generate build/flash table with port selection controls."""
        yield Static("Port", classes="header")
        yield Static("Library", classes="header")
        yield Static("Example", classes="header")
        yield Static("Flash", classes="header")
        for port in self.ports:
            yield Static(port, classes="port")

            lib_choices = [(opt.display_name, opt.id) for opt in self.logic.lib_options]
            yield Select(lib_choices, prompt="-- Select Lib --")

            example_choices = [(opt.display_name, opt.id) for opt in self.logic.example_options]
            yield Select(example_choices, prompt="-- Select Example --")

            yield Button(
                f"⚡ Flash {port}",
                id=f"flash-{port}",
                classes="flash-button",
                disabled=True
            )

    def compose(self) -> ComposeResult:
        """Compose the tab layout with table, log viewer, and toolbar."""
        with Grid(id="table"):
            yield from self._build_table()
        yield RichLogExtended(
            highlight=True,
            id="status",
            name="testarea",
            max_lines=2000,
            buffer_size=20,
            flush_interval=0.05,
            markup=True,
        )
        with Container(id="build-flash-actions"):
            yield Button("🧹 Clear Log", id="clear-log", classes="toolbar-button")
            if self._debug:
                yield Button("📊 Log Statistics", id="richlog-statistics", classes="toolbar-button")
            yield Button("❌ Quit", id="quit", classes="toolbar-button")

    def on_mount(self) -> None:
        """Initialize tab when mounted - connect logger and display configuration info."""
        RichLogHandler.set_rich_log(self.query_one(RichLogExtended))
        self.python_logger.info(f"Kconfig: {self.logic.kconfig_path}")
        self.python_logger.info(f"SDKconfig: {self.logic.sdkconfig_path}")
        self.python_logger.info(
            f"Loaded {len(self.logic.lib_options)} lib options, {len(self.logic.example_options)} example options")
        self.python_logger.debug("=== LIB OPTIONS ===")
        for opt in self.logic.lib_options:
            self.python_logger.debug(f"  {opt.id}: {opt.display_name}")

        self.python_logger.debug("=== EXAMPLE OPTIONS ===")
        for opt in self.logic.example_options:
            depends_str = f", depends_on: {opt.depends_on}" if opt.depends_on else ""
            self.python_logger.debug(f"  {opt.id}: {opt.display_name}{depends_str}")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle library/example selection changes and update flash button state based on dependencies."""
        grid = self.query_one("#table")
        all_selects = list(grid.query(Select))
        select_index = -1
        for i, select in enumerate(all_selects):
            if select == event.select:
                select_index = i
                break

        if select_index >= 0:
            row_index = select_index // 2
            lib_select = all_selects[row_index * 2]
            example_select = all_selects[row_index * 2 + 1]
            flash_buttons = [btn for btn in grid.query(Button) if btn.id and btn.id.startswith("flash-")]
            if row_index < len(flash_buttons):
                flash_button = flash_buttons[row_index]
                lib_selected = lib_select.value is not None and lib_select.value != Select.BLANK
                example_selected = example_select.value is not None and example_select.value != Select.BLANK
                dependencies_ok = True
                if lib_selected and example_selected:
                    dependencies_ok = self.logic.check_dependencies(lib_select.value, example_select.value)

                    example_option = self.logic.get_example_option_by_id(example_select.value)
                    if example_option and example_option.depends_on:
                        lib_option = self.logic.get_lib_option_by_id(lib_select.value)
                        msg_str = (
                            f"Dependency check: {example_select.value} requires {example_option.depends_on}, "
                            f"selected {lib_option.id if lib_option else 'unknown'} -> "
                            f"{'OK' if dependencies_ok else 'FAIL'}"
                        )
                        if dependencies_ok:
                            self.python_logger.debug(msg_str)
                        else:
                            self.python_logger.warning(msg_str)
                all_conditions_met = lib_selected and example_selected and dependencies_ok
                flash_button.disabled = not all_conditions_met

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("flash-"):
            self._on_flash_pressed(event)
        elif event.button.id == "clear-log":
            self._on_clear_log_pressed(event)
        elif event.button.id == "quit":
            self.run_worker(self.gui_app.action_quit(), exclusive=False)
        elif event.button.id == "richlog-statistics":
            self._on_show_stats_pressed(event)

    def _on_flash_pressed(self, event: Button.Pressed) -> None:
        """Handle flash button press - start async build and flash process."""
        port = event.button.id.replace("flash-", "")
        grid = self.query_one("#table")
        buttons = [btn for btn in grid.query(Button) if btn.id and btn.id.startswith("flash-")]

        for i, btn in enumerate(buttons):
            if btn == event.button:
                base_idx = 4 + i * 4
                lib_select = grid.children[base_idx + 1]
                example_select = grid.children[base_idx + 2]
                self.run_worker(
                    self.logic.config_compile_flash(port, lib_select.value, example_select.value),
                    name=f"flash_{port}"
                )
                break
    
    def _on_clear_log_pressed(self, event: Button.Pressed) -> None:
        """Clear only the Build & Flash RichLog"""
        try:
            rich_log = self.query_one("#status", RichLogExtended)
            rich_log.clear()
            self.python_logger.info("Log cleared")
        except Exception as e:
            self.python_logger.error(f"Failed to clear build log: {e}")

    def _on_show_stats_pressed(self, event: Button.Pressed) -> None:
        """Display RichLogExtended performance statistics for debugging."""
        rich_log = self.query_one(RichLogExtended)
        rich_log.print_stats()
