# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
'''

from textual.app import ComposeResult
from textual.containers import Grid
from textual.containers import Grid, Container
from textual.widgets import Static, Button, TextArea
from py.log.rich_log_handler import RichLogHandler
from py.monitor.shell_monitor_logic import ShellMonitorLogic


class SerialMonitorsTab(Container):


    """Tab with monitor controls (left) and monitor outputs (right)."""
    def __init__(self, ports, python_logger: RichLogHandler) -> None:
        super().__init__(id="serial-monitors-tab")
        self.ports = ports
        self.python_logger = python_logger
        self.active_monitor_logs = {}  # port -> TextArea widget
        
        # Initialize monitor logic
        self.monitor_logic = ShellMonitorLogic(
            read_timeout=0.01,  # 10ms read timeout
            write_timeout=0.01  # 10ms write timeout
        )

    def _monitor_table(self) -> ComposeResult:
        # headers
        yield Static("Port", classes="header")
        yield Static("Open", classes="header")
        yield Static("Run", classes="header")

        # rows
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
        if  event.button.id and event.button.id.startswith("open-"):
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
            # Hide the monitor log for this port
            event.button.label = "+ Show"
            
            # If monitoring is active, stop it first
            if self.monitor_logic.is_monitoring(port):
                self._stop_monitoring(port)
                # Update run button to Start state
                run_button = self.query_one(f"#run-{port}")
                run_button.label = "▶ Start"
                self.python_logger.debug(f"Stopped monitoring for port {port} due to hide")
            
            self._remove_monitor_log(port)
            self.python_logger.debug(f"Hide monitor for port {port}")

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
            self._stop_monitoring(port)
            self.python_logger.debug(f"Stop monitoring port {port}")

    def _add_monitor_log(self, port: str) -> None:
        """Add TextArea for monitoring port output"""
        try:
            right_panel = self.query_one("#serial-right-panel")
            
            # Remove placeholder if it exists
            try:
                placeholder = self.query_one("#monitor-placeholder")
                placeholder.remove()
            except:
                pass
            
            # Create container for this port's monitor
            monitor_container = Container(id=f"monitor-container-{port}", classes="monitor-container")
            title = Static(f"Monitor: {port}", classes="monitor-title")
            serial_logger = TextArea(
                id=f"serial-logger-{port}",
                classes="serial-logger",
                read_only=True
            )
            
            # Mount container and then add content
            right_panel.mount(monitor_container)
            monitor_container.mount(title)
            monitor_container.mount(serial_logger)
            
            # Store reference for later removal
            self.active_monitor_logs[port] = serial_logger
            
            # Rebalance heights
            self._rebalance_monitor_logs()
            
            self.python_logger.debug(f"Added monitor log for port {port}")
            
        except Exception as e:
            self.python_logger.error(f"Failed to add monitor log for port {port}: {e}")

    def _remove_monitor_log(self, port: str) -> None:
        """Remove TextArea for monitoring port output"""
        try:
            container = self.query_one(f"#monitor-container-{port}")
            container.remove()
            
            # Remove from tracking
            if port in self.active_monitor_logs:
                del self.active_monitor_logs[port]
            
            # Check if we need to restore placeholder
            right_panel = self.query_one("#serial-right-panel")
            if not list(right_panel.query(Container)):
                placeholder = Static("Monitor Output - monitors will appear here", id="monitor-placeholder")
                right_panel.mount(placeholder)
            else:
                # Rebalance remaining logs
                self._rebalance_monitor_logs()
                
            self.python_logger.debug(f"Removed monitor log for port {port}")
            
        except Exception as e:
            self.python_logger.error(f"Failed to remove monitor log for port {port}: {e}")

    def _rebalance_monitor_logs(self) -> None:
        """Rebalance heights of all active serial loggers"""
        try:
            if not self.active_monitor_logs:
                return
                
            right_panel = self.query_one("#serial-right-panel")
            containers = list(right_panel.query(Container))
            
            if not containers:
                return
                
            # Calculate height per container (equal distribution)
            height_per_container = f"{100 // len(containers)}%"
            
            for container in containers:
                container.styles.height = height_per_container
                
            self.python_logger.debug(f"Rebalanced {len(containers)} serial loggers")
            
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

    def _stop_monitoring(self, port: str) -> None:
        """Stop monitoring process for given port"""
        try:
            success = self.monitor_logic.stop_monitor_for_gui(port)
            
            if success:
                self.python_logger.debug(f"Successfully stopped monitoring for port {port}")
            else:
                self.python_logger.warning(f"No active monitoring found for port {port}")
                
        except Exception as e:
            self.python_logger.error(f"Error stopping monitoring for port {port}: {e}")