# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''

'''
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.containers import Grid, Container
from textual.widgets import Static, Button, Select
from py.log.rich_log_extended import RichLogExtended
from py.app_logic import FlashApp
from py.log.rich_log_handler import RichLogHandler

class BuildFlashTab(Container):
    """Tab with Build & Flash table, status log and toolbar."""

    def __init__(
            self, 
            logic: FlashApp,
            gui_app: App,
            ports: [str], 
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
        # headers
        yield Static("Port", classes="header")
        yield Static("Library", classes="header")
        yield Static("Example", classes="header")
        yield Static("Flash", classes="header")

        # rows
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
        # table
        with Grid(id="table"):
            yield from self._build_table()

        # log
        yield RichLogExtended(
            highlight=True,
            id="status",
            name="testarea",
            max_lines=2000,
            buffer_size=20,
            flush_interval=0.05,
            markup=True,
        )

        # toolbar
        with Container(id="build-flash-actions"):
            yield Button("🧹 Clear Log", id="clear-log", classes="toolbar-button")
            if self._debug:
                yield Button("📊 Log Statistics", id="richlog-statistics", classes="toolbar-button")
            yield Button("❌ Quit", id="quit", classes="toolbar-button")

    def on_mount(self) -> None:
        # Connect the logging handler to RichLogExtended
        RichLogHandler.set_rich_log(self.query_one(RichLogExtended))

        # Log config file paths and loaded options on startup
        self.python_logger.info(f"Kconfig: {self.logic.kconfig_path}")
        self.python_logger.info(f"SDKconfig: {self.logic.sdkconfig_path}")
        self.python_logger.info(
            f"Loaded {len(self.logic.lib_options)} lib options, {len(self.logic.example_options)} example options")

        # Debug: Print all loaded options
        self.python_logger.debug("=== LIB OPTIONS ===")
        for opt in self.logic.lib_options:
            self.python_logger.debug(f"  {opt.id}: {opt.display_name}")

        self.python_logger.debug("=== EXAMPLE OPTIONS ===")
        for opt in self.logic.example_options:
            depends_str = f", depends_on: {opt.depends_on}" if opt.depends_on else ""
            self.python_logger.debug(f"  {opt.id}: {opt.display_name}{depends_str}")

    # --- Event handlers --------------------------------------------------------

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
                            self.python_logger.debug(msg_str)
                        else:
                            self.python_logger.warning(msg_str)

                # Button is enabled only when both are selected AND dependencies are satisfied
                all_conditions_met = lib_selected and example_selected and dependencies_ok
                flash_button.disabled = not all_conditions_met

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("flash-"):
            self._on_flash_pressed(event)
        elif event.button.id == "clear-log":
            self._on_clear_log_pressed(event)
        elif event.button.id == "quit":
            self.gui_app.action_quit()
        elif event.button.id == "richlog-statistics":
            self._on_show_stats_pressed(event)

    def _on_flash_pressed(self, event: Button.Pressed) -> None:
        port = event.button.id.replace("flash-", "")

        # Find corresponding selects for this button
        grid = self.query_one("#table")
        buttons = [btn for btn in grid.query(Button) if btn.id and btn.id.startswith("flash-")]

        for i, btn in enumerate(buttons):
            if btn == event.button:
                # 4 columns now: port, lib, example, flash
                base_idx = 4 + i * 4 # Skip header row (5 items), then i rows of 5 columns each
                lib_select = grid.children[base_idx + 1]  # lib is 2nd column (index 1)
                example_select = grid.children[base_idx + 2]  # example is 3rd column (index 2)

                # Execute flash sequence asynchronously to keep GUI responsive
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

    # For debugging purposes, add a button to show statistics
    def _on_show_stats_pressed(self, event: Button.Pressed) -> None:
        """Show RichLogExtended statistics"""
        rich_log = self.query_one(RichLogExtended)
        rich_log.print_stats()