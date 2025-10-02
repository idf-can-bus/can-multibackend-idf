# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Serial monitor tab for Textual GUI application.
Provides controls for managing multiple serial port monitors with show/hide and start/stop functionality.
Monitors continue running in background when hidden and preserve their log history.
'''

from textual.app import ComposeResult
from textual.containers import Grid, Container
from textual.widgets import Static, Button, Log
from py.log.rich_log_handler import RichLogHandler
from py.monitor.shell_monitor_logic import ShellMonitorLogic


class SerialMonitorsTab(Container):
    """
    Serial monitoring tab with dual-panel layout.
    Left panel: control buttons for show/hide and start/stop monitoring.
    Right panel: log outputs for each monitored port.
    Supports multiple concurrent monitors with automatic height distribution.
    """
    def __init__(
            self,
            ports,
            python_logger: RichLogHandler,
            monitor_logic: ShellMonitorLogic,
            max_log_lines: int = 500
    ) -> None:
        super().__init__(id="serial-monitors-tab")
        self.ports = ports
        self.python_logger = python_logger
        self.max_log_lines = max_log_lines
        self.active_monitor_logs = {}  # port -> Log widget
        self.monitor_visibility = {}  # port -> bool (True = visible, False = hidden)
        
        # Initialize monitor logic
        self.monitor_logic = monitor_logic

    def _monitor_table(self) -> ComposeResult:
        """Generate monitor control table with headers and rows for each port."""
        yield Static("Port", classes="header")
        yield Static("Open", classes="header")
        yield Static("Run", classes="header")
        for port in self.ports:
            yield Static(port, classes="port-name")
            yield Button("+ Show", id=f"open-{port}", classes="open-button", disabled=False)
            yield Button("▶ Start", id=f"run-{port}", classes="run-button", disabled=False)

    def compose(self) -> ComposeResult:
        with Container(id="serial-left-panel"):
            yield Static("Monitor Controls", classes="header")
            with Grid(id="monitor-table"):
                yield from self._monitor_table()

        with Container(id="serial-right-panel"):
            yield Static("Monitor Output - monitors will appear here", id="monitor-placeholder")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("open-"):
            self._on_open_pressed(event)
        elif event.button.id and event.button.id.startswith("run-"):
            self._on_run_pressed(event)
        
    def _on_open_pressed(self, event: Button.Pressed) -> None:
        """Handle open/hide button toggle for port visibility"""
        port = event.button.id.replace("open-", "")
        current_text = str(event.button.label)
        
        if "Show" in current_text:
            # Show the monitor log for this port
            event.button.label = "- Hide"
            self._add_monitor_log(port)
            self.python_logger.debug(f"Show monitor for port {port}")
        else:
            # Hide the monitor log for this port (monitoring continues in background)
            event.button.label = "+ Show"
            self._remove_monitor_log(port)
            self.python_logger.debug(f"Hide monitor for port {port} (monitoring continues)")

    def _on_run_pressed(self, event: Button.Pressed) -> None:
        """Handle start/stop button toggle for port monitoring"""
        port = event.button.id.replace("run-", "")
        current_text = str(event.button.label)
        
        if "Start" in current_text:
            # Start monitoring
            event.button.label = "▣ Stop"
            
            # If monitor log is not visible, show it first
            if port not in self.active_monitor_logs:
                # Update open button to Hide state
                open_button = self.query_one(f"#open-{port}")
                open_button.label = "- Hide"
                self._add_monitor_log(port)
                self.python_logger.debug(f"Auto-opened monitor log for port {port}")
            
            self._start_monitoring(port)
            self.python_logger.debug(f"Start monitoring port {port}")
        else:
            # Stop monitoring
            event.button.label = "▶ Start"
            # Run async stop in background
            self.app.run_worker(self._stop_monitoring(port), exclusive=False)
            self.python_logger.debug(f"Stop monitoring port {port}")

    def _add_monitor_log(self, port: str) -> None:
        """Show Log for monitoring port output (create if doesn't exist)"""
        try:
            right_panel = self.query_one("#serial-right-panel")
            
            # Check if Log already exists
            if port in self.active_monitor_logs:
                # Log exists, just show it
                container = self.query_one(f"#monitor-container-{port}")
                container.styles.display = "block"
                self.monitor_visibility[port] = True
                self.python_logger.debug(f"Showed existing monitor log for port {port}")
            else:
                # Create new Log
                monitor_container = Container(id=f"monitor-container-{port}", classes="monitor-container")
                title = Static(f"Monitor: {port}", classes="monitor-title")
                serial_logger = Log(
                    id=f"serial-logger-{port}",
                    classes="serial-logger",
                    max_lines=self.max_log_lines
                )
                
                # Mount container and then add content
                right_panel.mount(monitor_container)
                monitor_container.mount(title)
                monitor_container.mount(serial_logger)
                
                # Store reference
                self.active_monitor_logs[port] = serial_logger
                self.monitor_visibility[port] = True
                
                self.python_logger.debug(f"Created monitor log for port {port}")
            
            # Remove placeholder if it exists
            try:
                placeholder = self.query_one("#monitor-placeholder")
                placeholder.remove()
            except:
                pass
            
            # Rebalance heights of visible logs
            self._rebalance_monitor_logs()
            
        except Exception as e:
            self.python_logger.error(f"Failed to add monitor log for port {port}: {e}")

    def _remove_monitor_log(self, port: str) -> None:
        """Hide Log for monitoring port output (don't delete it)"""
        try:
            if port in self.active_monitor_logs:
                container = self.query_one(f"#monitor-container-{port}")
                container.styles.display = "none"
                self.monitor_visibility[port] = False
                
                self.python_logger.debug(f"Hidden monitor log for port {port}")
                
                # Check if we need to restore placeholder (all logs hidden)
                if not any(self.monitor_visibility.values()):
                    right_panel = self.query_one("#serial-right-panel")
                    try:
                        # Only add placeholder if it doesn't exist
                        self.query_one("#monitor-placeholder")
                    except:
                        placeholder = Static("Monitor Output - monitors will appear here", id="monitor-placeholder")
                        right_panel.mount(placeholder)
                else:
                    # Rebalance remaining visible logs
                    self._rebalance_monitor_logs()
            
        except Exception as e:
            self.python_logger.error(f"Failed to hide monitor log for port {port}: {e}")

    def _rebalance_monitor_logs(self) -> None:
        """Rebalance heights of all visible serial loggers"""
        try:
            if not self.active_monitor_logs:
                return
            
            # Count visible logs
            visible_count = sum(1 for visible in self.monitor_visibility.values() if visible)
            
            if visible_count == 0:
                return
                
            # Calculate height per visible container (equal distribution)
            height_per_container = f"{100 // visible_count}%"
            
            # Apply height only to visible containers
            for port, visible in self.monitor_visibility.items():
                if visible:
                    try:
                        container = self.query_one(f"#monitor-container-{port}")
                        container.styles.height = height_per_container
                    except:
                        pass
                
            self.python_logger.debug(f"Rebalanced {visible_count} visible serial loggers")
            
        except Exception as e:
            self.python_logger.error(f"Failed to rebalance serial loggers: {e}")

    def _start_monitoring(self, port: str) -> None:
        """Start monitoring process for given port"""
        try:
            # Check if serial logger exists for this port
            if port not in self.active_monitor_logs:
                self.python_logger.warning(f"Cannot start monitoring for port {port} - no serial logger visible")
                return
                
            serial_logger = self.active_monitor_logs[port]
            
            # Start monitoring via shell monitor logic
            success = self.monitor_logic.start_monitor_for_gui(
                port=port,
                monitor_log_widget=serial_logger,
                gui_run_worker_method=self.app.run_worker
            )
            
            if success:
                self.python_logger.debug(f"Successfully started monitoring for port {port}")
            else:
                self.python_logger.error(f"Failed to start monitoring for port {port}")
                
        except Exception as e:
            self.python_logger.error(f"Error starting monitoring for port {port}: {e}")

    async def _stop_monitoring(self, port: str) -> None:
        """Stop monitoring process for given port"""
        try:
            success = await self.monitor_logic.stop_monitor_for_gui(port)
            
            if success:
                self.python_logger.debug(f"Successfully stopped monitoring for port {port}")
            else:
                self.python_logger.warning(f"No active monitoring found for port {port}")
                
        except Exception as e:
            self.python_logger.error(f"Error stopping monitoring for port {port}: {e}")
